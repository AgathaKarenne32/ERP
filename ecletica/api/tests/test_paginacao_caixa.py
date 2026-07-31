from fastapi.testclient import TestClient


def _abrir_e_fechar_caixa(client: TestClient, headers: dict) -> None:
    resposta = client.post("/caixa/abrir", headers=headers)
    assert resposta.status_code == 201
    resposta = client.patch("/caixa/fechar", headers=headers)
    assert resposta.status_code == 200


def test_v1_listar_caixas_respeita_limit(client: TestClient, headers_caixa: dict):
    for _ in range(5):
        _abrir_e_fechar_caixa(client, headers_caixa)

    resposta = client.get("/v1/caixa?limit=2", headers=headers_caixa)
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert len(corpo["items"]) == 2
    assert corpo["limit"] == 2
    assert corpo["offset"] == 0


def test_v1_listar_caixas_total_reflete_contagem_real_nao_so_pagina_atual(client: TestClient, headers_caixa: dict):
    for _ in range(7):
        _abrir_e_fechar_caixa(client, headers_caixa)

    resposta = client.get("/v1/caixa?limit=3&offset=6", headers=headers_caixa)
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert len(corpo["items"]) == 1
    assert corpo["total"] == 7
    assert corpo["offset"] == 6


def test_listar_caixas_sem_versao_continua_devolvendo_array_puro(client: TestClient, headers_caixa: dict):
    """Garante que a rota antiga (sem /v1) não virou breaking change."""
    _abrir_e_fechar_caixa(client, headers_caixa)

    resposta = client.get("/caixa", headers=headers_caixa)
    assert resposta.status_code == 200
    assert isinstance(resposta.json(), list)
