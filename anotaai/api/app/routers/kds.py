import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..core.db import get_session
from ..core.deps import get_current_loja_id
from ..models import StatusProducao, TicketProducao
from ..schemas import TicketProducaoOut

router = APIRouter(prefix="/kds", tags=["kds"])


@router.get("/fila", response_model=list[TicketProducaoOut])
def fila_producao(
    session: Session = Depends(get_session),
    id_loja: uuid.UUID = Depends(get_current_loja_id),
) -> list[TicketProducao]:
    """RF07: fila de preparo para a equipe de cozinha (KDS)."""
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
) -> TicketProducao:
    ticket = session.get(TicketProducao, ticket_id)
    if not ticket or ticket.id_loja != id_loja:
        raise HTTPException(status_code=404, detail="Ticket não encontrado")
    ticket.status_producao = novo_status
    ticket.atualizado_em = datetime.now(timezone.utc)
    session.add(ticket)
    session.commit()
    session.refresh(ticket)
    return ticket
