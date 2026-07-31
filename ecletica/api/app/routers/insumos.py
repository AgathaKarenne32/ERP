import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from ..core.db import get_session
from ..core.deps import get_current_loja_id, require_roles
from ..models import Insumo, MovimentoEstoque, PapelUsuario, TipoMovimentoEstoque
from ..schemas import InsumoCreate, InsumoOut, MovimentoEstoqueCreate, MovimentoEstoqueOut

router = APIRouter(prefix="/insumos", tags=["insumos"])


@router.get("", response_model=list[InsumoOut])
def listar_insumos(
    session: Session = Depends(get_session),
    id_loja: uuid.UUID = Depends(get_current_loja_id),
) -> list[Insumo]:
    return list(session.exec(select(Insumo).where(Insumo.id_loja == id_loja)).all())


@router.get("/abaixo-do-minimo", response_model=list[InsumoOut])
def insumos_abaixo_do_minimo(
    session: Session = Depends(get_session),
    id_loja: uuid.UUID = Depends(get_current_loja_id),
    _usuario=Depends(require_roles(PapelUsuario.ADMIN, PapelUsuario.GERENTE)),
) -> list[Insumo]:
    """Item 9 do plano de próxima onda: sinaliza insumo que vai faltar antes
    que falte de verdade (ex: gelo sexta à noite). Estritamente abaixo do
    mínimo - no mínimo exato ainda não é alerta."""
    return list(
        session.exec(
            select(Insumo)
            .where(Insumo.id_loja == id_loja)
            .where(Insumo.qtd_estoque < Insumo.estoque_minimo)
        ).all()
    )


@router.post("", response_model=InsumoOut, status_code=201)
def criar_insumo(
    payload: InsumoCreate,
    session: Session = Depends(get_session),
    id_loja: uuid.UUID = Depends(get_current_loja_id),
    _usuario=Depends(require_roles(PapelUsuario.ADMIN, PapelUsuario.GERENTE)),
) -> Insumo:
    insumo = Insumo(id_loja=id_loja, **payload.model_dump())
    session.add(insumo)
    session.commit()
    session.refresh(insumo)
    return insumo


@router.post("/{insumo_id}/movimentar", response_model=InsumoOut)
def movimentar_insumo(
    insumo_id: uuid.UUID,
    payload: MovimentoEstoqueCreate,
    session: Session = Depends(get_session),
    id_loja: uuid.UUID = Depends(get_current_loja_id),
    _usuario=Depends(require_roles(PapelUsuario.ADMIN, PapelUsuario.GERENTE)),
) -> Insumo:
    """Movimentação manual de estoque: ENTRADA (compra) soma, AJUSTE (perda/
    quebra/correção) soma ou subtrai. SAIDA_VENDA é reservada para a baixa
    automática em /vendas/baixa-estoque e não é aceita aqui."""
    if payload.tipo == TipoMovimentoEstoque.SAIDA_VENDA:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SAIDA_VENDA só pode ser gerada pela baixa automática de venda",
        )

    insumo = session.get(Insumo, insumo_id)
    if not insumo or insumo.id_loja != id_loja:
        raise HTTPException(status_code=404, detail="Insumo não encontrado")

    nova_qtd = insumo.qtd_estoque + payload.quantidade
    if nova_qtd < 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Movimentação deixaria o estoque negativo",
        )

    insumo.qtd_estoque = nova_qtd
    session.add(insumo)
    session.add(
        MovimentoEstoque(
            id_loja=id_loja,
            id_insumo=insumo_id,
            tipo=payload.tipo,
            quantidade=payload.quantidade,
            referencia=payload.referencia,
        )
    )
    session.commit()
    session.refresh(insumo)
    return insumo


@router.get("/{insumo_id}/movimentos", response_model=list[MovimentoEstoqueOut])
def listar_movimentos(
    insumo_id: uuid.UUID,
    session: Session = Depends(get_session),
    id_loja: uuid.UUID = Depends(get_current_loja_id),
) -> list[MovimentoEstoque]:
    insumo = session.get(Insumo, insumo_id)
    if not insumo or insumo.id_loja != id_loja:
        raise HTTPException(status_code=404, detail="Insumo não encontrado")

    return list(
        session.exec(
            select(MovimentoEstoque)
            .where(MovimentoEstoque.id_insumo == insumo_id)
            .order_by(MovimentoEstoque.criado_em.desc())
        ).all()
    )
