import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..core.db import get_session
from ..core.deps import get_current_loja_id, require_roles
from ..models import FichaTecnica, PapelUsuario, Produto
from ..schemas import FichaTecnicaItemCreate, ProdutoCreate, ProdutoOut

router = APIRouter(prefix="/produtos", tags=["produtos"])


@router.get("", response_model=list[ProdutoOut])
def listar_produtos(
    session: Session = Depends(get_session),
    id_loja: uuid.UUID = Depends(get_current_loja_id),
) -> list[Produto]:
    return list(session.exec(select(Produto).where(Produto.id_loja == id_loja)).all())


@router.post("", response_model=ProdutoOut, status_code=201)
def criar_produto(
    payload: ProdutoCreate,
    session: Session = Depends(get_session),
    id_loja: uuid.UUID = Depends(get_current_loja_id),
    _usuario=Depends(require_roles(PapelUsuario.ADMIN, PapelUsuario.GERENTE)),
) -> Produto:
    produto = Produto(id_loja=id_loja, **payload.model_dump())
    session.add(produto)
    session.commit()
    session.refresh(produto)
    return produto


@router.put("/{produto_id}/ficha-tecnica", status_code=204)
def definir_ficha_tecnica(
    produto_id: uuid.UUID,
    itens: list[FichaTecnicaItemCreate],
    session: Session = Depends(get_session),
    id_loja: uuid.UUID = Depends(get_current_loja_id),
    _usuario=Depends(require_roles(PapelUsuario.ADMIN, PapelUsuario.GERENTE)),
) -> None:
    """Substitui a ficha técnica do produto (RN01: base para a baixa de estoque)."""
    produto = session.get(Produto, produto_id)
    if not produto or produto.id_loja != id_loja:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    existentes = session.exec(
        select(FichaTecnica).where(FichaTecnica.id_produto == produto_id)
    ).all()
    for item in existentes:
        session.delete(item)

    for item in itens:
        session.add(
            FichaTecnica(
                id_produto=produto_id,
                id_insumo=item.id_insumo,
                qtd_utilizada=item.qtd_utilizada,
            )
        )
    session.commit()
