import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from ..core.db import get_session
from ..core.deps import verify_internal_token
from ..models import FechamentoCaixa, FichaTecnica, Insumo, MovimentoEstoque, TipoMovimentoEstoque
from ..schemas import BaixaEstoqueRequest

router = APIRouter(prefix="/vendas", tags=["vendas"])


@router.post(
    "/baixa-estoque",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(verify_internal_token)],
)
def baixar_estoque(
    payload: BaixaEstoqueRequest,
    session: Session = Depends(get_session),
) -> None:
    """RN01: abate o estoque dos insumos conforme a ficha técnica de cada produto vendido.
    RN02: bloqueia toda a venda (nenhum insumo é descontado) se faltar estoque de algum.
    Se houver um caixa aberto para a loja, soma o valor da venda nele."""
    consumo_por_insumo: dict[uuid.UUID, float] = {}

    for item in payload.itens:
        fichas = session.exec(
            select(FichaTecnica).where(FichaTecnica.id_produto == item.id_produto)
        ).all()
        for ficha in fichas:
            consumo_por_insumo[ficha.id_insumo] = (
                consumo_por_insumo.get(ficha.id_insumo, 0)
                + ficha.qtd_utilizada * item.quantidade
            )

    if consumo_por_insumo:
        insumos = {
            insumo.id: insumo
            for insumo in session.exec(
                select(Insumo)
                .where(Insumo.id_loja == payload.id_loja)
                .where(Insumo.id.in_(consumo_por_insumo.keys()))
                .with_for_update()
            ).all()
        }

        faltantes = [
            str(id_insumo)
            for id_insumo, qtd_necessaria in consumo_por_insumo.items()
            if insumos.get(id_insumo) is None or insumos[id_insumo].qtd_estoque < qtd_necessaria
        ]
        if faltantes:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Estoque insuficiente para os insumos: {', '.join(faltantes)}",
            )

        for id_insumo, qtd_necessaria in consumo_por_insumo.items():
            insumo = insumos[id_insumo]
            insumo.qtd_estoque -= qtd_necessaria
            session.add(insumo)
            session.add(
                MovimentoEstoque(
                    id_loja=payload.id_loja,
                    id_insumo=id_insumo,
                    tipo=TipoMovimentoEstoque.SAIDA_VENDA,
                    quantidade=qtd_necessaria,
                    referencia=payload.referencia,
                )
            )

    caixa_aberto = session.exec(
        select(FechamentoCaixa)
        .where(FechamentoCaixa.id_loja == payload.id_loja)
        .where(FechamentoCaixa.fechado_em.is_(None))
        .with_for_update()
    ).first()
    if caixa_aberto:
        caixa_aberto.valor_total += payload.valor_total
        session.add(caixa_aberto)

    session.commit()
