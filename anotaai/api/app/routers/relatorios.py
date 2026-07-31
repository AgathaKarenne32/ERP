import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..core.db import get_session
from ..core.deps import get_current_loja_id, require_roles
from ..models import Comanda, ItemComanda, PapelOperador, StatusComanda
from ..schemas import ProdutoMaisVendidoOut, RelatorioVendasOut, ValorPorFormaPagamentoOut

router = APIRouter(prefix="/relatorios", tags=["relatorios"])


def _comandas_pagas_no_periodo(
    session: Session,
    id_loja: uuid.UUID,
    inicio: datetime | None,
    fim: datetime | None,
) -> list[Comanda]:
    query = (
        select(Comanda)
        .where(Comanda.id_loja == id_loja)
        .where(Comanda.status == StatusComanda.PAGA)
    )
    if inicio:
        query = query.where(Comanda.fechada_em >= inicio)
    if fim:
        query = query.where(Comanda.fechada_em <= fim)
    return list(session.exec(query).all())


@router.get("/vendas", response_model=RelatorioVendasOut)
def relatorio_vendas(
    inicio: datetime | None = None,
    fim: datetime | None = None,
    session: Session = Depends(get_session),
    id_loja: uuid.UUID = Depends(get_current_loja_id),
    _operador=Depends(require_roles(PapelOperador.ADMIN, PapelOperador.GERENTE, PapelOperador.CAIXA)),
) -> RelatorioVendasOut:
    """RF10: total vendido, quantidade de comandas pagas e ticket médio no
    período. Considera só comandas PAGA — nunca ABERTA ou CANCELADA."""
    comandas = _comandas_pagas_no_periodo(session, id_loja, inicio, fim)
    # Valor líquido (após desconto) - precisa bater com o que de fato entrou
    # no caixa em fechar_comanda, não o valor de tabela dos itens.
    total = sum(c.valor_total - c.desconto_total for c in comandas)
    quantidade = len(comandas)
    ticket_medio = total / quantidade if quantidade else 0.0

    agregados: dict[str, dict[str, float]] = {}
    for comanda in comandas:
        if comanda.forma_pagamento is None:
            continue
        agregado = agregados.setdefault(
            comanda.forma_pagamento, {"valor_total": 0.0, "quantidade_comandas": 0}
        )
        agregado["valor_total"] += comanda.valor_total - comanda.desconto_total
        agregado["quantidade_comandas"] += 1

    por_forma_pagamento = [
        ValorPorFormaPagamentoOut(forma_pagamento=forma, **dados)
        for forma, dados in agregados.items()
    ]

    return RelatorioVendasOut(
        periodo_inicio=inicio,
        periodo_fim=fim,
        total_vendas=total,
        quantidade_comandas=quantidade,
        ticket_medio=ticket_medio,
        por_forma_pagamento=por_forma_pagamento,
    )


@router.get("/produtos-mais-vendidos", response_model=list[ProdutoMaisVendidoOut])
def produtos_mais_vendidos(
    inicio: datetime | None = None,
    fim: datetime | None = None,
    limite: int = 10,
    session: Session = Depends(get_session),
    id_loja: uuid.UUID = Depends(get_current_loja_id),
    _operador=Depends(require_roles(PapelOperador.ADMIN, PapelOperador.GERENTE, PapelOperador.CAIXA)),
) -> list[ProdutoMaisVendidoOut]:
    """RF10: ranking de produtos por valor vendido no período."""
    comandas = _comandas_pagas_no_periodo(session, id_loja, inicio, fim)
    ids_comandas = [c.id for c in comandas]

    itens: list[ItemComanda] = []
    if ids_comandas:
        itens = list(
            session.exec(
                select(ItemComanda).where(ItemComanda.id_comanda.in_(ids_comandas))
            ).all()
        )

    agregados: dict[str, dict[str, float]] = {}
    for item in itens:
        agregado = agregados.setdefault(
            item.nome_produto, {"quantidade_total": 0.0, "valor_total": 0.0}
        )
        agregado["quantidade_total"] += item.quantidade
        agregado["valor_total"] += item.quantidade * item.preco_aplicado

    ranking = sorted(
        agregados.items(), key=lambda kv: kv[1]["valor_total"], reverse=True
    )[:limite]

    return [
        ProdutoMaisVendidoOut(nome_produto=nome, **dados) for nome, dados in ranking
    ]
