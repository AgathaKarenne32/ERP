import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from jose import JWTError
from sqlmodel import Session, select

from ..core.db import get_session
from ..core.deps import get_current_loja_id, require_roles
from ..core.realtime import canal_kds, cliente_redis_async, publicar_atualizacao_kds
from ..core.security import decode_access_token
from ..models import PapelOperador, StatusProducao, TicketProducao
from ..schemas import TicketProducaoOut

router = APIRouter(prefix="/kds", tags=["kds"])


@router.get("/fila", response_model=list[TicketProducaoOut])
def fila_producao(
    session: Session = Depends(get_session),
    id_loja: uuid.UUID = Depends(get_current_loja_id),
) -> list[TicketProducao]:
    """RF07: fila de preparo para a equipe de cozinha (KDS) — via polling.
    Veja também GET /kds/ws para a versão em tempo real."""
    return list(
        session.exec(
            select(TicketProducao)
            .where(TicketProducao.id_loja == id_loja)
            .where(TicketProducao.status_producao != StatusProducao.ENTREGUE)
        ).all()
    )


@router.patch("/tickets/{ticket_id}", response_model=TicketProducaoOut)
def atualizar_status(
    ticket_id: uuid.UUID,
    novo_status: StatusProducao,
    session: Session = Depends(get_session),
    id_loja: uuid.UUID = Depends(get_current_loja_id),
    _operador=Depends(
        require_roles(PapelOperador.ADMIN, PapelOperador.GERENTE, PapelOperador.COZINHA, PapelOperador.GARCOM)
    ),
) -> TicketProducao:
    ticket = session.get(TicketProducao, ticket_id)
    if not ticket or ticket.id_loja != id_loja:
        raise HTTPException(status_code=404, detail="Ticket não encontrado")
    ticket.status_producao = novo_status
    ticket.atualizado_em = datetime.now(timezone.utc)
    session.add(ticket)
    session.commit()
    session.refresh(ticket)

    publicar_atualizacao_kds(
        id_loja, TicketProducaoOut.model_validate(ticket).model_dump(mode="json")
    )

    return ticket


@router.websocket("/ws")
async def kds_websocket(
    websocket: WebSocket,
    token: str = Query(...),
    session: Session = Depends(get_session),
) -> None:
    """RF07: alimenta o KDS em tempo real via WebSocket + Redis Pub/Sub, no
    lugar do polling em /kds/fila. Autenticação via ?token=<jwt> na query —
    WebSocket de navegador não permite header Authorization customizado."""
    try:
        payload = decode_access_token(token)
        id_loja = uuid.UUID(payload["id_loja"])
    except (JWTError, KeyError, ValueError):
        await websocket.close(code=4401)
        return

    await websocket.accept()

    fila_atual = session.exec(
        select(TicketProducao)
        .where(TicketProducao.id_loja == id_loja)
        .where(TicketProducao.status_producao != StatusProducao.ENTREGUE)
    ).all()
    await websocket.send_json(
        {
            "tipo": "snapshot",
            "tickets": [
                TicketProducaoOut.model_validate(t).model_dump(mode="json")
                for t in fila_atual
            ],
        }
    )

    pubsub = cliente_redis_async().pubsub()
    await pubsub.subscribe(canal_kds(id_loja))
    try:
        async for mensagem in pubsub.listen():
            if mensagem["type"] != "message":
                continue
            await websocket.send_json(
                {"tipo": "ticket_atualizado", "ticket": json.loads(mensagem["data"])}
            )
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe(canal_kds(id_loja))
        await pubsub.close()
