from unittest.mock import MagicMock

import httpx
import pytest

from app import tasks


def _resposta_produto(id_produto: str = "11111111-1111-1111-1111-111111111111") -> MagicMock:
    resposta = MagicMock(spec=httpx.Response)
    resposta.status_code = 200
    resposta.raise_for_status.return_value = None
    resposta.json.return_value = {"id": id_produto, "nome": "Caipirinha", "preco_venda": 15}
    return resposta


def test_normalizar_itens_resolve_sku_externo_no_produto(monkeypatch):
    mock_get = MagicMock(return_value=_resposta_produto())
    monkeypatch.setattr("httpx.get", mock_get)

    itens = tasks._normalizar_itens("IFOOD", [{"sku_externo": "SKU-1", "quantity": 2, "price": 15}])

    assert itens == [
        {
            "id_produto": "11111111-1111-1111-1111-111111111111",
            "nome_produto": "Caipirinha",
            "quantidade": 2,
            "preco_aplicado": 15,
        }
    ]
    mock_get.assert_called_once()
    assert mock_get.call_args.kwargs["params"] == {"provedor": "IFOOD", "sku_externo": "SKU-1"}


def test_normalizar_itens_usa_id_como_fallback_de_sku_externo(monkeypatch):
    mock_get = MagicMock(return_value=_resposta_produto())
    monkeypatch.setattr("httpx.get", mock_get)

    tasks._normalizar_itens("WHATSAPP", [{"id": "SKU-2", "quantidade": 1, "preco_aplicado": 10}])

    assert mock_get.call_args.kwargs["params"]["sku_externo"] == "SKU-2"


def test_normalizar_itens_propaga_erro_quando_sku_nao_mapeado(monkeypatch):
    resposta = MagicMock(spec=httpx.Response)
    resposta.status_code = 404
    resposta.raise_for_status.side_effect = httpx.HTTPStatusError(
        "not found", request=MagicMock(), response=resposta
    )
    mock_get = MagicMock(return_value=resposta)
    monkeypatch.setattr("httpx.get", mock_get)

    with pytest.raises(httpx.HTTPStatusError):
        tasks._normalizar_itens("IFOOD", [{"sku_externo": "SKU-DESCONHECIDO"}])
