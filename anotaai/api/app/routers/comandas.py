import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..core.db import get_session
from ..core.deps import get_current_loja_id, require_roles
from ..models import Comanda, ItemComanda, PapelOperador, StatusComanda, TicketProducao
from ..schemas import ComandaCreate, ComandaOut, ItemComandaCreate, ItemComandaOut

router = APIRouter(prefix="/comandas", tags=["comandas"])


@router.post("", response_model=ComandaOut, status_code=201)
def abrir_comanda(
    payload: ComandaCreate,
    session: Session = Depends(get_session),
    id_loja: uuid.UUID = Depends(get_current_loja_id),
) -> Comanda:
    comanda = Comanda(id_loja=id_loja, identificador=payload.identificador)
    session.add(comanda)
    session.commit()
    session.refresh(comanda)
    return comanda


@router.get("", response_model=list[ComandaOut])
def listar_comandas(
    session: Session = Depends(get_session),
    id_loja: uuid.UUID = Depends(get_current_loja_id),
) -> list[Comanda]:
    return list(session.exec(select(Comanda).where(Comanda.id_loja == id_loja)).all())


@router.post("/{comanda_id}/itens", response_model=ItemComandaOut, status_code=201)
def adicionar_item(
    comanda_id: uuid.UUID,
    payload: ItemComandaCreate,
    session: Session = Depends(get_session),
    id_loja: uuid.UUID = Depends(get_current_loja_id),
) -> ItemComanda:
    """RF06: consolida pedidos físicos (SALAO) e virtuais (IFOOD/WHATSAPP) na
    mesma comanda. RN04: preço e nome são gravados como snapshot no item."""
    comanda = session.get(Comanda, comanda_id)
    if not comanda or comanda.id_loja != id_loja:
        raise HTTPException(status_code=404, detail="Comanda não encontrada")
    if comanda.status != StatusComanda.ABERTA:
        # RN03: comanda paga/cancelada não recebe novos itens
        raise HTTPException(status_code=409, detail="Comanda já está fechada")

    item = ItemComanda(id_loja=id_loja, id_comanda=comanda.id, **payload.model_dump())
    session.add(item)
    comanda.valor_total += item.quantidade * item.preco_aplicado
    session.add(comanda)
    session.commit()
    session.refresh(item)

    # Cria o ticket de produção correspondente para o KDS.
    ticket = TicketProducao(id_loja=id_loja, id_item_comanda=item.id)
    session.add(ticket)
    session.commit()

    return item


@router.patch("/{comanda_id}/fechar", response_model=ComandaOut)
def fechar_comanda(
    comanda_id: uuid.UUID,
    session: Session = Depends(get_session),
    id_loja: uuid.UUID = Depends(get_current_loja_id),
    _operador=Depends(
        require_roles(PapelOperador.CAIXA, PapelOperador.ADMIN, PapelOperador.GERENTE)
    ),
) -> Comanda:
    """RN03: o status só pode ser alterado para PAGA pelo módulo de Caixa (PDV)."""
    comanda = session.get(Comanda, comanda_id)
    if not comanda or comanda.id_loja != id_loja:
        raise HTTPException(status_code=404, detail="Comanda não encontrada")

    comanda.status = StatusComanda.PAGA
    comanda.fechada_em = datetime.now(timezone.utc)
    session.add(comanda)
    session.commit()
    session.refresh(comanda)
    return comanda
