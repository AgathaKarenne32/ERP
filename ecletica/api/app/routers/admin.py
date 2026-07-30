import uuid

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session, select

from ..core.db import get_session
from ..core.deps import exigir_usuario_painel_admin
from ..core.security import create_access_token, verify_password
from ..core.templates import templates
from ..models import MapeamentoSkuExterno, PapelUsuario, Produto, ProvedorExterno, Usuario

router = APIRouter(prefix="/admin", tags=["admin"], include_in_schema=False)


@router.get("/login", response_class=HTMLResponse)
def formulario_login(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "admin/login.html", {"erro": None, "usuario": None})


@router.post("/login")
def enviar_login(
    request: Request,
    email: str = Form(...),
    senha: str = Form(...),
    session: Session = Depends(get_session),
):
    usuario = session.exec(select(Usuario).where(Usuario.email == email)).first()
    credenciais_validas = usuario and usuario.ativo and verify_password(senha, usuario.senha_hash)
    if not credenciais_validas or usuario.papel not in (PapelUsuario.ADMIN, PapelUsuario.GERENTE):
        return templates.TemplateResponse(
            request,
            "admin/login.html",
            {"erro": "Email ou senha inválidos", "usuario": None},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    token = create_access_token(
        subject=str(usuario.id),
        extra_claims={"papel": usuario.papel.value, "id_loja": str(usuario.id_loja)},
    )
    resposta = RedirectResponse(url="/admin/produtos", status_code=status.HTTP_303_SEE_OTHER)
    resposta.set_cookie(key="access_token", value=token, httponly=True, samesite="lax")
    return resposta


@router.post("/logout")
def logout() -> RedirectResponse:
    resposta = RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    resposta.delete_cookie("access_token")
    return resposta


def _mapeamentos_por_produto(session: Session, produtos: list[Produto]) -> dict[uuid.UUID, list[MapeamentoSkuExterno]]:
    if not produtos:
        return {}
    mapeamentos = session.exec(
        select(MapeamentoSkuExterno).where(
            MapeamentoSkuExterno.id_produto.in_([produto.id for produto in produtos])
        )
    ).all()
    agrupado: dict[uuid.UUID, list[MapeamentoSkuExterno]] = {produto.id: [] for produto in produtos}
    for mapeamento in mapeamentos:
        agrupado[mapeamento.id_produto].append(mapeamento)
    return agrupado


@router.get("/produtos", response_class=HTMLResponse)
def listar_produtos_admin(
    request: Request,
    session: Session = Depends(get_session),
    usuario: Usuario = Depends(exigir_usuario_painel_admin),
) -> HTMLResponse:
    produtos = list(session.exec(select(Produto).where(Produto.id_loja == usuario.id_loja)).all())
    return templates.TemplateResponse(
        request,
        "admin/produtos.html",
        {
            "usuario": usuario,
            "produtos": produtos,
            "mapeamentos_por_produto": _mapeamentos_por_produto(session, produtos),
        },
    )


@router.post("/produtos")
def criar_produto_admin(
    nome: str = Form(...),
    preco_venda: float = Form(...),
    categoria: str = Form(""),
    session: Session = Depends(get_session),
    usuario: Usuario = Depends(exigir_usuario_painel_admin),
) -> RedirectResponse:
    produto = Produto(id_loja=usuario.id_loja, nome=nome, preco_venda=preco_venda, categoria=categoria or None)
    session.add(produto)
    session.commit()
    return RedirectResponse(url="/admin/produtos", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/produtos/{produto_id}/mapear-sku", response_class=HTMLResponse)
def mapear_sku_admin(
    request: Request,
    produto_id: uuid.UUID,
    provedor: ProvedorExterno = Form(...),
    sku_externo: str = Form(...),
    session: Session = Depends(get_session),
    usuario: Usuario = Depends(exigir_usuario_painel_admin),
) -> HTMLResponse:
    produto = session.get(Produto, produto_id)
    if not produto or produto.id_loja != usuario.id_loja:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    existente = session.exec(
        select(MapeamentoSkuExterno)
        .where(MapeamentoSkuExterno.provedor == provedor)
        .where(MapeamentoSkuExterno.sku_externo == sku_externo)
    ).first()
    erro = None
    if existente:
        erro = "Esse SKU externo já está mapeado para um produto"
    else:
        session.add(MapeamentoSkuExterno(id_produto=produto_id, provedor=provedor, sku_externo=sku_externo))
        session.commit()

    mapeamentos = list(
        session.exec(select(MapeamentoSkuExterno).where(MapeamentoSkuExterno.id_produto == produto_id)).all()
    )
    return templates.TemplateResponse(
        request,
        "admin/_produto_skus.html",
        {"produto": produto, "mapeamentos_por_produto": {produto_id: mapeamentos}, "erro": erro},
    )
