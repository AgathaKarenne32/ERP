from fastapi.testclient import TestClient

from app.core.db import get_session
from app.main import app


def test_health_live_nao_depende_de_nada(client: TestClient):
    resposta = client.get("/health/live")
    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok"}


def test_health_ready_ok_quando_banco_responde(client: TestClient):
    resposta = client.get("/health/ready")
    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok"}


def test_health_ready_falha_com_banco_indisponivel(client: TestClient):
    class _SessaoQuebrada:
        def execute(self, *args, **kwargs):
            raise RuntimeError("banco fora do ar")

    def _get_session_quebrada():
        yield _SessaoQuebrada()

    app.dependency_overrides[get_session] = _get_session_quebrada
    try:
        resposta = client.get("/health/ready")
        assert resposta.status_code == 503
    finally:
        app.dependency_overrides.pop(get_session, None)
