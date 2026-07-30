from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models import Loja, PapelUsuario, Produto, Usuario


def test_login_com_credenciais_invalidas_mostra_erro(client: TestClient):
    resposta = client.post(
        "/admin/login", data={"email": "inexistente@teste.local", "senha": "errada"}
    )
    assert resposta.status_code == 401
    assert "Email ou senha inválidos" in resposta.text


def test_login_sucesso_seta_cookie_e_redireciona(client: TestClient, usuario_admin: Usuario):
    resposta = client.post(
        "/admin/login",
        data={"email": "admin@teste.local", "senha": "senha123"},
        follow_redirects=False,
    )
    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/admin/produtos"
    assert "access_token" in resposta.cookies


def test_login_rejeita_papel_sem_permissao_de_painel(session: Session, client: TestClient, loja: Loja):
    from app.core.security import hash_password

    operador = Usuario(
        id_loja=loja.id,
        nome="Caixa Teste",
        email="caixa-painel@teste.local",
        senha_hash=hash_password("senha123"),
        papel=PapelUsuario.CAIXA,
    )
    session.add(operador)
    session.commit()

    resposta = client.post(
        "/admin/login", data={"email": "caixa-painel@teste.local", "senha": "senha123"}
    )
    assert resposta.status_code == 401


def test_produtos_sem_cookie_redireciona_para_login(client: TestClient):
    resposta = client.get("/admin/produtos", follow_redirects=False)
    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/admin/login"


def _logar(client: TestClient) -> None:
    resposta = client.post(
        "/admin/login",
        data={"email": "admin@teste.local", "senha": "senha123"},
        follow_redirects=False,
    )
    assert resposta.status_code == 303


def test_fluxo_completo_criar_produto_e_mapear_sku(client: TestClient, session: Session, usuario_admin: Usuario):
    _logar(client)

    resposta_lista_vazia = client.get("/admin/produtos")
    assert resposta_lista_vazia.status_code == 200
    assert "Nenhum produto cadastrado" in resposta_lista_vazia.text

    resposta_criar = client.post(
        "/admin/produtos",
        data={"nome": "Caipirinha", "preco_venda": "15.00", "categoria": "Drinks"},
        follow_redirects=False,
    )
    assert resposta_criar.status_code == 303

    produto = session.exec(select(Produto).where(Produto.id_loja == usuario_admin.id_loja)).first()
    assert produto is not None
    assert produto.nome == "Caipirinha"

    resposta_lista = client.get("/admin/produtos")
    assert resposta_lista.status_code == 200
    assert "Caipirinha" in resposta_lista.text
    assert "Nenhum SKU externo mapeado" in resposta_lista.text

    resposta_mapear = client.post(
        f"/admin/produtos/{produto.id}/mapear-sku",
        data={"provedor": "IFOOD", "sku_externo": "SKU-PAINEL-1"},
    )
    assert resposta_mapear.status_code == 200
    assert "SKU-PAINEL-1" in resposta_mapear.text

    resposta_duplicada = client.post(
        f"/admin/produtos/{produto.id}/mapear-sku",
        data={"provedor": "IFOOD", "sku_externo": "SKU-PAINEL-1"},
    )
    assert resposta_duplicada.status_code == 200
    assert "já está mapeado" in resposta_duplicada.text


def test_logout_remove_cookie_e_bloqueia_acesso(client: TestClient, usuario_admin: Usuario):
    _logar(client)
    assert client.get("/admin/produtos").status_code == 200

    resposta_logout = client.post("/admin/logout", follow_redirects=False)
    assert resposta_logout.status_code == 303

    resposta_apos_logout = client.get("/admin/produtos", follow_redirects=False)
    assert resposta_apos_logout.status_code == 303
    assert resposta_apos_logout.headers["location"] == "/admin/login"
