import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..core.db import get_session
from ..core.deps import get_current_loja_id, require_roles
from ..core.ecletica_client import solicitar_baixa_estoque, solicitar_credito_fidelidade
from ..models import Comanda, ItemComanda, PapelOperador, StatusComanda, TicketProducao
from ..schemas import (
    ComandaCancelarRequest,
    ComandaCreate,
    ComandaOut,
    ComandaVincularClienteRequest,
    ItemComandaCreate,
    ItemComandaOut,
    TransferirItensRequest,
)

router = APIRouter(prefix="/comandas", tags=["comandas"])


@router.post("", response_model=ComandaOut, status_code=201)
def abrir_comanda(
    payload: ComandaCreate,
    session: Session = Depends(get_session),
    id_loja: uuid.UUID = Depends(get_current_loja_id),
) -> Comanda:
    comanda = Comanda(
        id_loja=id_loja,
        identificador=payload.identificador,
        id_cliente=payload.id_cliente,
    )
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


@router.patch("/{comanda_id}/cliente", response_model=ComandaOut)
def vincular_cliente(
    comanda_id: uuid.UUID,
    payload: ComandaVincularClienteRequest,
    session: Session = Depends(get_session),
    id_loja: uuid.UUID = Depends(get_current_loja_id),
) -> Comanda:
    """Vincula (ou troca) o cliente de uma comanda aberta — pré-requisito
    pra fidelidade (RN05), que credita pontos com base nesse vínculo."""
    comanda = session.get(Comanda, comanda_id)
    if not comanda or comanda.id_loja != id_loja:
        raise HTTPException(status_code=404, detail="Comanda não encontrada")
    if comanda.status != StatusComanda.ABERTA:
        raise HTTPException(status_code=409, detail="Só é possível vincular cliente numa comanda aberta")

    comanda.id_cliente = payload.id_cliente
    session.add(comanda)
    session.commit()
    session.refresh(comanda)
    return comanda


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


@router.post("/{comanda_id}/transferir-itens", response_model=ComandaOut)
def transferir_itens(
    comanda_id: uuid.UUID,
    payload: TransferirItensRequest,
    session: Session = Depends(get_session),
    id_loja: uuid.UUID = Depends(get_current_loja_id),
) -> Comanda:
    """RF05: move itens de uma comanda pra outra (ex: cliente trocou de mesa,
    ou fundir contas no fechamento). As duas comandas precisam estar ABERTA."""
    origem = session.get(Comanda, comanda_id)
    if not origem or origem.id_loja != id_loja:
        raise HTTPException(status_code=404, detail="Comanda de origem não encontrada")
    if origem.status != StatusComanda.ABERTA:
        raise HTTPException(status_code=409, detail="Só é possível transferir itens de uma comanda aberta")

    if payload.id_comanda_destino == origem.id:
        raise HTTPException(status_code=400, detail="Comanda de destino deve ser diferente da origem")

    destino = session.get(Comanda, payload.id_comanda_destino)
    if not destino or destino.id_loja != id_loja:
        raise HTTPException(status_code=404, detail="Comanda de destino não encontrada")
    if destino.status != StatusComanda.ABERTA:
        raise HTTPException(status_code=409, detail="Só é possível transferir itens para uma comanda aberta")

    itens = session.exec(
        select(ItemComanda)
        .where(ItemComanda.id_comanda == comanda_id)
        .where(ItemComanda.id.in_(payload.id_itens))
    ).all()

    encontrados = {item.id for item in itens}
    faltantes = set(payload.id_itens) - encontrados
    if faltantes:
        raise HTTPException(
            status_code=404,
            detail=f"Itens não encontrados na comanda de origem: {', '.join(str(i) for i in faltantes)}",
        )

    for item in itens:
        valor_item = item.quantidade * item.preco_aplicado
        item.id_comanda = destino.id
        origem.valor_total -= valor_item
        destino.valor_total += valor_item
        session.add(item)

    session.add(origem)
    session.add(destino)
    session.commit()
    session.refresh(origem)
    return origem


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
    if comanda.status != StatusComanda.ABERTA:
        raise HTTPException(status_code=409, detail="Só é possível fechar uma comanda aberta")

    itens = session.exec(
        select(ItemComanda).where(ItemComanda.id_comanda == comanda_id)
    ).all()
    itens_baixa = [
        {"id_produto": str(item.id_produto), "quantidade": item.quantidade}
        for item in itens
    ]

    # RN01/RN02: dá baixa no estoque na ecletica-api antes de confirmar o pagamento,
    # e soma o valor da venda no caixa aberto (se houver). Se faltar insumo, isto
    # levanta HTTPException(409) e a comanda não fecha.
    solicitar_baixa_estoque(
        id_loja=id_loja,
        itens=itens_baixa,
        referencia=str(comanda_id),
        valor_total=comanda.valor_total,
    )

    comanda.status = StatusComanda.PAGA
    comanda.fechada_em = datetime.now(timezone.utc)
    session.add(comanda)
    session.commit()
    session.refresh(comanda)

    # RN05: credita fidelidade só depois do pagamento confirmado, e só se
    # houver cliente vinculado. Falha aqui não desfaz o pagamento.
    if comanda.id_cliente:
        solicitar_credito_fidelidade(
            id_loja=id_loja,
            id_cliente=comanda.id_cliente,
            valor_gasto=comanda.valor_total,
            referencia=str(comanda_id),
        )

    return comanda


@router.patch("/{comanda_id}/cancelar", response_model=ComandaOut)
def cancelar_comanda(
    comanda_id: uuid.UUID,
    payload: ComandaCancelarRequest,
    session: Session = Depends(get_session),
    id_loja: uuid.UUID = Depends(get_current_loja_id),
    _operador=Depends(
        require_roles(PapelOperador.CAIXA, PapelOperador.ADMIN, PapelOperador.GERENTE)
    ),
) -> Comanda:
    """RN03 (extensão): cancela uma comanda aberta, sem baixa de estoque (nada
    foi vendido). Comanda já paga ou já cancelada não pode ser cancelada de novo."""
    comanda = session.get(Comanda, comanda_id)
    if not comanda or comanda.id_loja != id_loja:
        raise HTTPException(status_code=404, detail="Comanda não encontrada")
    if comanda.status != StatusComanda.ABERTA:
        raise HTTPException(status_code=409, detail="Só é possível cancelar uma comanda aberta")

    comanda.status = StatusComanda.CANCELADA
    comanda.fechada_em = datetime.now(timezone.utc)
    comanda.motivo_cancelamento = payload.motivo
    session.add(comanda)
    session.commit()
    session.refresh(comanda)
    return comanda
