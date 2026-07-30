import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.rate_limit import limiter
from app.core.security import hash_password
from app.main import app
from app.models import Loja, PapelUsuario, Usuario


@pytest.fixture
def usuario_para_login(session: Session, loja):
    usuario = Usuario(
        id_loja=loja.id,
        nome="Teste Login",
        email="login@teste.com",
        senha_hash=hash_password("senha123"),
        papel=PapelUsuario.GARCOM,
    )
    session.add(usuario)
    session.commit()
    session.refresh(usuario)
    return usuario


def test_login_success(client: TestClient, usuario_para_login: Usuario):
    response = client.post(
        "/auth/login",
        json={"email": "login@teste.com", "senha": "senha123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials(client: TestClient, usuario_para_login: Usuario):
    response = client.post(
        "/auth/login",
        json={"email": "login@teste.com", "senha": "senha_errada"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Email ou senha inválidos"


def test_login_nonexistent_email(client: TestClient):
    response = client.post(
        "/auth/login",
        json={"email": "nao_existe@teste.com", "senha": "senha123"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Email ou senha inválidos"


def test_login_rate_limiting(client: TestClient, usuario_para_login: Usuario):
    """Test that login endpoint is rate limited to 5 requests per minute per IP."""
    limiter.reset()

    email = "login@teste.com"
    senha = "senha123"

    responses = []
    for i in range(6):
        response = client.post(
            "/auth/login",
            json={"email": email, "senha": senha},
            headers={"X-Forwarded-For": "127.0.0.1"},
        )
        responses.append(response.status_code)

    assert responses[:5] == [200, 200, 200, 200, 200]
    assert responses[5] == 429
