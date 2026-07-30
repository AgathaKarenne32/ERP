import uuid
from unittest.mock import MagicMock

import httpx
import pytest
from fastapi import HTTPException

from app.core.ecletica_client import solicitar_baixa_estoque


def _resposta_ok() -> MagicMock:
    resposta = MagicMock(spec=httpx.Response)
    resposta.status_code = 204
    resposta.raise_for_status.return_value = None
    return resposta


def test_solicitar_baixa_estoque_sucesso_na_primeira_tentativa(monkeypatch):
    mock_post = MagicMock(return_value=_resposta_ok())
    monkeypatch.setattr("httpx.post", mock_post)

    solicitar_baixa_estoque(id_loja=uuid.uuid4(), itens=[], referencia="ref-1", valor_total=10)

    assert mock_post.call_count == 1


def test_solicitar_baixa_estoque_recupera_de_timeout_transitorio(monkeypatch):
    mock_post = MagicMock(side_effect=[httpx.ConnectTimeout("timeout"), _resposta_ok()])
    monkeypatch.setattr("httpx.post", mock_post)
    monkeypatch.setattr("time.sleep", lambda *_: None)

    solicitar_baixa_estoque(id_loja=uuid.uuid4(), itens=[], referencia="ref-2", valor_total=10)

    assert mock_post.call_count == 2


def test_solicitar_baixa_estoque_esgota_tentativas_e_retorna_503(monkeypatch):
    mock_post = MagicMock(side_effect=httpx.ConnectTimeout("timeout"))
    monkeypatch.setattr("httpx.post", mock_post)
    monkeypatch.setattr("time.sleep", lambda *_: None)

    with pytest.raises(HTTPException) as exc_info:
        solicitar_baixa_estoque(id_loja=uuid.uuid4(), itens=[], referencia="ref-3", valor_total=10)

    assert exc_info.value.status_code == 503
    assert mock_post.call_count == 3


def test_solicitar_baixa_estoque_nao_reten_em_409(monkeypatch):
    resposta = MagicMock(spec=httpx.Response)
    resposta.status_code = 409
    resposta.json.return_value = {"detail": "Estoque insuficiente."}
    mock_post = MagicMock(return_value=resposta)
    monkeypatch.setattr("httpx.post", mock_post)

    with pytest.raises(HTTPException) as exc_info:
        solicitar_baixa_estoque(id_loja=uuid.uuid4(), itens=[], referencia="ref-4", valor_total=10)

    assert exc_info.value.status_code == 409
    assert mock_post.call_count == 1
