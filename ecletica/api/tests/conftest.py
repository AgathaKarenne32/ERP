import os

os.environ.setdefault("ECLETICA_SECRET_KEY", "test-secret-ecletica")
os.environ.setdefault("INTERNAL_API_TOKEN", "test-internal-token")

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.core.config import settings
from app.core.db import get_session
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models import Loja, PapelUsuario, Usuario


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def loja(session: Session) -> Loja:
    loja = Loja(nome="Bar Teste", cnpj="00.000.000/0001-00")
    session.add(loja)
    session.commit()
    session.refresh(loja)
    return loja


@pytest.fixture
def usuario_admin(session: Session, loja: Loja) -> Usuario:
    usuario = Usuario(
        id_loja=loja.id,
        nome="Admin Teste",
        email="admin@teste.local",
        senha_hash=hash_password("senha123"),
        papel=PapelUsuario.ADMIN,
    )
    session.add(usuario)
    session.commit()
    session.refresh(usuario)
    return usuario


@pytest.fixture
def headers_admin(usuario_admin: Usuario) -> dict:
    token = create_access_token(
        subject=str(usuario_admin.id),
        extra_claims={"papel": usuario_admin.papel.value, "id_loja": str(usuario_admin.id_loja)},
    )
    return {"Authorization": f"Bearer {token}"}


def _criar_usuario(session: Session, loja: Loja, papel: PapelUsuario, email: str) -> Usuario:
    usuario = Usuario(
        id_loja=loja.id,
        nome=f"{papel.value} Teste",
        email=email,
        senha_hash=hash_password("senha123"),
        papel=papel,
    )
    session.add(usuario)
    session.commit()
    session.refresh(usuario)
    return usuario


def _headers(usuario: Usuario) -> dict:
    token = create_access_token(
        subject=str(usuario.id),
        extra_claims={"papel": usuario.papel.value, "id_loja": str(usuario.id_loja)},
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def headers_caixa(session: Session, loja: Loja) -> dict:
    usuario = _criar_usuario(session, loja, PapelUsuario.CAIXA, "caixa@teste.local")
    return _headers(usuario)


@pytest.fixture
def headers_garcom(session: Session, loja: Loja) -> dict:
    usuario = _criar_usuario(session, loja, PapelUsuario.GARCOM, "garcom@teste.local")
    return _headers(usuario)


@pytest.fixture
def headers_interno() -> dict:
    return {"X-Internal-Token": settings.internal_api_token}
