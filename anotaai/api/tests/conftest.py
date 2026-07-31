import os

os.environ.setdefault("ANOTAAI_SECRET_KEY", "test-secret-anotaai")
os.environ.setdefault("INTERNAL_API_TOKEN", "test-internal-token")
os.environ.setdefault("ANOTAAI_IFOOD_WEBHOOK_SECRET", "test-ifood-secret")
os.environ.setdefault("ANOTAAI_META_APP_SECRET", "test-meta-app-secret")
os.environ.setdefault("ANOTAAI_META_VERIFY_TOKEN", "test-meta-verify-token")
# Evita exigir um Redis real no CI: rate limit fica em memória durante os testes,
# só usa o storage distribuído (item 8 do plano de próxima onda) em produção.
os.environ.setdefault("ANOTAAI_RATE_LIMIT_STORAGE_URI", "memory://")

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.core.config import settings
from app.core.db import get_session
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models import IntegracaoLoja, Operador, OrigemPedido, PapelOperador


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(autouse=True)
def _sem_chamadas_externas(monkeypatch):
    """Testes de unidade da anotaai-api não devem depender da ecletica-api
    nem do Redis estarem no ar — essas integrações viram no-op aqui."""
    monkeypatch.setattr("app.routers.comandas.solicitar_baixa_estoque", lambda **kwargs: None)
    monkeypatch.setattr("app.routers.comandas.solicitar_credito_fidelidade", lambda **kwargs: None)
    monkeypatch.setattr("app.routers.comandas.publicar_atualizacao_kds", lambda *a, **k: None)
    monkeypatch.setattr("app.routers.kds.publicar_atualizacao_kds", lambda *a, **k: None)


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def id_loja() -> uuid.UUID:
    return uuid.uuid4()


def _criar_operador(session: Session, id_loja: uuid.UUID, papel: PapelOperador, email: str) -> Operador:
    operador = Operador(
        id_loja=id_loja,
        nome=f"{papel.value} Teste",
        email=email,
        senha_hash=hash_password("senha123"),
        papel=papel,
    )
    session.add(operador)
    session.commit()
    session.refresh(operador)
    return operador


def _headers(operador: Operador) -> dict:
    token = create_access_token(
        subject=str(operador.id),
        extra_claims={"papel": operador.papel.value, "id_loja": str(operador.id_loja)},
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def headers_caixa(session: Session, id_loja: uuid.UUID) -> dict:
    operador = _criar_operador(session, id_loja, PapelOperador.CAIXA, "caixa@teste.local")
    return _headers(operador)


@pytest.fixture
def headers_garcom(session: Session, id_loja: uuid.UUID) -> dict:
    operador = _criar_operador(session, id_loja, PapelOperador.GARCOM, "garcom@teste.local")
    return _headers(operador)


@pytest.fixture
def headers_cozinha(session: Session, id_loja: uuid.UUID) -> dict:
    operador = _criar_operador(session, id_loja, PapelOperador.COZINHA, "cozinha@teste.local")
    return _headers(operador)


@pytest.fixture
def headers_admin(session: Session, id_loja: uuid.UUID) -> dict:
    operador = _criar_operador(session, id_loja, PapelOperador.ADMIN, "admin@teste.local")
    return _headers(operador)


@pytest.fixture
def headers_interno() -> dict:
    return {"X-Internal-Token": settings.internal_api_token}


@pytest.fixture
def loja_inicializada(session: Session, id_loja: uuid.UUID) -> None:
    """Garante que existe pelo menos um Operador e uma IntegracaoLoja
    mapeando os identificadores externos usados nos testes — necessário
    pra ingestao_externa rotear pra loja certa (RN06, multi-loja)."""
    _criar_operador(session, id_loja, PapelOperador.ADMIN, "admin@teste.local")
    session.add(
        IntegracaoLoja(id_loja=id_loja, provedor=OrigemPedido.IFOOD, identificador_externo="MERCHANT-TESTE")
    )
    session.add(
        IntegracaoLoja(id_loja=id_loja, provedor=OrigemPedido.WHATSAPP, identificador_externo="NUMERO-TESTE")
    )
    session.commit()
