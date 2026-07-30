import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..core.db import get_session
from ..core.deps import get_current_loja_id, require_roles, verify_internal_token
from ..models import FichaTecnica, MapeamentoSkuExterno, PapelUsuario, Produto, ProvedorExterno
from ..schemas import (
    FichaTecnicaItemCreate,
    MapeamentoSkuCreate,
    MapeamentoSkuOut,
    ProdutoCreate,
    ProdutoOut,
    ProdutoResolvidoOut,
)

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


@router.post("/{produto_id}/mapear-sku", response_model=MapeamentoSkuOut, status_code=201)
def mapear_sku(
    produto_id: uuid.UUID,
    payload: MapeamentoSkuCreate,
    session: Session = Depends(get_session),
    id_loja: uuid.UUID = Depends(get_current_loja_id),
    _usuario=Depends(require_roles(PapelUsuario.ADMIN, PapelUsuario.GERENTE)),
) -> MapeamentoSkuExterno:
    """Cadastra o de-para entre o SKU do provedor externo (iFood/WhatsApp) e
    um produto do cardápio — usado pelo anotaai-worker para resolver pedidos
    externos em produtos reais."""
    produto = session.get(Produto, produto_id)
    if not produto or produto.id_loja != id_loja:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    existente = session.exec(
        select(MapeamentoSkuExterno)
        .where(MapeamentoSkuExterno.provedor == payload.provedor)
        .where(MapeamentoSkuExterno.sku_externo == payload.sku_externo)
    ).first()
    if existente:
        raise HTTPException(status_code=409, detail="Esse SKU externo já está mapeado para um produto")

    mapeamento = MapeamentoSkuExterno(id_produto=produto_id, **payload.model_dump())
    session.add(mapeamento)
    session.commit()
    session.refresh(mapeamento)
    return mapeamento


@router.get(
    "/resolver-sku",
    response_model=ProdutoResolvidoOut,
    dependencies=[Depends(verify_internal_token)],
)
def resolver_sku(provedor: ProvedorExterno, sku_externo: str, session: Session = Depends(get_session)) -> Produto:
    """Chamado pelo anotaai-worker (token interno) para traduzir o SKU de um
    provedor externo no produto real do cardápio antes de injetar a comanda."""
    mapeamento = session.exec(
        select(MapeamentoSkuExterno)
        .where(MapeamentoSkuExterno.provedor == provedor)
        .where(MapeamentoSkuExterno.sku_externo == sku_externo)
    ).first()
    if not mapeamento:
        raise HTTPException(status_code=404, detail="Nenhum produto mapeado para esse SKU externo")

    produto = session.get(Produto, mapeamento.id_produto)
    if not produto:
        raise HTTPException(status_code=404, detail="Produto mapeado não existe mais")
    return produto
