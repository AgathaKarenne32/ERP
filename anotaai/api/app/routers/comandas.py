import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlmodel import Session, select

from ..core.db import get_session
from ..core.deps import get_current_loja_id, require_roles, verify_internal_token
from ..core.ecletica_client import solicitar_baixa_estoque, solicitar_credito_fidelidade
from ..core.realtime import publicar_atualizacao_kds
from ..models import Comanda, IntegracaoLoja, ItemComanda, PapelOperador, StatusComanda, TicketProducao
from ..schemas import (
    ComandaCancelarRequest,
    ComandaCreate,
    ComandaOut,
    ComandaVincularClienteRequest,
    IngestaoExternaRequest,
    ItemComandaCreate,
    ItemComandaOut,
    TicketProducaoOut,
    TransferirItensRequest,
)

router = APIRouter(prefix="/comandas", tags=["comandas"])


@router.post("", response_model=ComandaOut, status_code=201)
def abrir_comanda(
    payload: ComandaCreate,
    session: Session = Depends(get_session),
    id_loja: uuid.UUID = Depends(get_current_loja_id),
    _operador=Depends(
        require_roles(PapelOperador.ADMIN, PapelOperador.GERENTE, PapelOperador.CAIXA, PapelOperador.GARCOM)
    ),
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
    _operador=Depends(
        require_roles(PapelOperador.ADMIN, PapelOperador.GERENTE, PapelOperador.CAIXA, PapelOperador.GARCOM)
    ),
) -> list[Comanda]:
    return list(session.exec(select(Comanda).where(Comanda.id_loja == id_loja)).all())


@router.post(
    "/ingestao-externa",
    response_model=ComandaOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_internal_token)],
)
def ingestao_externa(
    payload: IngestaoExternaRequest,
    response: Response,
    session: Session = Depends(get_session),
) -> Comanda:
    """RF01/RF06: injeta um pedido vindo de um canal externo (iFood/WhatsApp)
    como uma comanda nova — mesmo ciclo de vida de uma venda de salão a partir
    daqui (KDS, fechamento, relatórios). Chamado pelo anotaai-worker depois
    de validar a assinatura do provedor e normalizar o payload.

    Idempotente: se o provedor reenviar o mesmo id_referencia_externa (comum
    em timeout de webhook), devolve a comanda ja criada em vez de duplicar.

    Roteamento multi-loja: o provedor não sabe nada sobre id_loja interno —
    resolve pela IntegracaoLoja cadastrada pra aquele provedor+identificador
    externo (merchant ID do iFood, número do WhatsApp Business). Sem
    mapeamento, rejeita explicitamente em vez de adivinhar uma loja."""
    integracao = session.exec(
        select(IntegracaoLoja)
        .where(IntegracaoLoja.provedor == payload.origem)
        .where(IntegracaoLoja.identificador_externo == payload.identificador_loja_externa)
    ).first()
    if not integracao:
        raise HTTPException(
            status_code=422,
            detail="Nenhuma loja configurada para esse provedor/identificador externo",
        )
    id_loja = integracao.id_loja

    existente = session.exec(
        select(Comanda)
        .where(Comanda.id_loja == id_loja)
        .where(Comanda.origem_externa == payload.origem)
        .where(Comanda.id_referencia_externa == payload.id_referencia_externa)
    ).first()
    if existente:
        response.status_code = status.HTTP_200_OK
        return existente

    identificador = f"{payload.origem.value} #{payload.id_referencia_externa}"
    comanda = Comanda(
        id_loja=id_loja,
        identificador=identificador,
        origem_externa=payload.origem,
        id_referencia_externa=payload.id_referencia_externa,
    )
    session.add(comanda)

    tickets_novos: list[TicketProducao] = []
    for item_payload in payload.itens:
        item = ItemComanda(
            id_loja=id_loja,
            id_comanda=comanda.id,
            origem=payload.origem,
            **item_payload.model_dump(),
        )
        session.add(item)
        comanda.valor_total += item.quantidade * item.preco_aplicado

        ticket = TicketProducao(id_loja=id_loja, id_item_comanda=item.id)
        session.add(ticket)
        tickets_novos.append(ticket)

    session.commit()
    session.refresh(comanda)

    for ticket in tickets_novos:
        session.refresh(ticket)
        publicar_atualizacao_kds(
            id_loja, TicketProducaoOut.model_validate(ticket).model_dump(mode="json")
        )

    return comanda


@router.patch("/{comanda_id}/cliente", response_model=ComandaOut)
def vincular_cliente(
    comanda_id: uuid.UUID,
    payload: ComandaVincularClienteRequest,
    session: Session = Depends(get_session),
    id_loja: uuid.UUID = Depends(get_current_loja_id),
    _operador=Depends(
        require_roles(PapelOperador.ADMIN, PapelOperador.GERENTE, PapelOperador.CAIXA, PapelOperador.GARCOM)
    ),
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
    _operador=Depends(
        require_roles(PapelOperador.ADMIN, PapelOperador.GERENTE, PapelOperador.CAIXA, PapelOperador.GARCOM)
    ),
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

    # Cria o ticket de produção correspondente para o KDS e avisa em tempo real.
    ticket = TicketProducao(id_loja=id_loja, id_item_comanda=item.id)
    session.add(ticket)
    session.commit()
    session.refresh(ticket)

    publicar_atualizacao_kds(
        id_loja, TicketProducaoOut.model_validate(ticket).model_dump(mode="json")
    )

    return item


@router.post("/{comanda_id}/transferir-itens", response_model=ComandaOut)
def transferir_itens(
    comanda_id: uuid.UUID,
    payload: TransferirItensRequest,
    session: Session = Depends(get_session),
    id_loja: uuid.UUID = Depends(get_current_loja_id),
    _operador=Depends(
        require_roles(PapelOperador.ADMIN, PapelOperador.GERENTE, PapelOperador.CAIXA, PapelOperador.GARCOM)
    ),
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
