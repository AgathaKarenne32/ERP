from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.rate_limit import limiter
from app.core.security import create_refresh_token, hash_password
from app.models import Loja, PapelUsuario, RefreshToken, Usuario


@pytest.fixture
def usuario(session: Session, loja: Loja) -> Usuario:
    usuario = Usuario(
        id_loja=loja.id,
        nome="Refresh Teste",
        email="refresh@teste.com",
        senha_hash=hash_password("senha123"),
        papel=PapelUsuario.GARCOM,
    )
    session.add(usuario)
    session.commit()
    session.refresh(usuario)
    return usuario


def _login(client: TestClient) -> dict:
    limiter.reset()
    response = client.post(
        "/auth/login",
        json={"email": "refresh@teste.com", "senha": "senha123"},
    )
    assert response.status_code == 200
    return response.json()


def test_login_retorna_access_e_refresh_token(client: TestClient, usuario: Usuario):
    data = _login(client)
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_refresh_emite_novo_par_de_tokens(client: TestClient, usuario: Usuario):
    limiter.reset()
    tokens = _login(client)

    response = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert response.status_code == 200
    novos_tokens = response.json()
    assert "access_token" in novos_tokens
    # O JWT pode ser idêntico se emitido no mesmo segundo (assinatura HS256 é
    # determinística para os mesmos claims); o que garante a rotação é o
    # refresh_token, que é sempre aleatório.
    assert novos_tokens["refresh_token"] != tokens["refresh_token"]


def test_refresh_rotaciona_e_invalida_token_antigo(client: TestClient, usuario: Usuario):
    limiter.reset()
    tokens = _login(client)

    primeira = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert primeira.status_code == 200

    reuso = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reuso.status_code == 401


def test_refresh_com_token_invalido_retorna_401(client: TestClient):
    response = client.post("/auth/refresh", json={"refresh_token": "token-que-nao-existe"})
    assert response.status_code == 401


def test_refresh_com_token_expirado_retorna_401(client: TestClient, session: Session, usuario: Usuario):
    token_bruto, token_hash = create_refresh_token()
    session.add(
        RefreshToken(
            id_usuario=usuario.id,
            token_hash=token_hash,
            expira_em=datetime.now(timezone.utc) - timedelta(days=1),
        )
    )
    session.commit()

    response = client.post("/auth/refresh", json={"refresh_token": token_bruto})
    assert response.status_code == 401


def test_logout_revoga_refresh_token(client: TestClient, usuario: Usuario):
    limiter.reset()
    tokens = _login(client)

    logout = client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert logout.status_code == 204

    reuso = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reuso.status_code == 401


def test_logout_com_token_inexistente_e_idempotente(client: TestClient):
    response = client.post("/auth/logout", json={"refresh_token": "token-que-nao-existe"})
    assert response.status_code == 204
