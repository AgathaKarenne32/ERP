from fastapi.testclient import TestClient


def _abrir_comanda(client: TestClient, headers: dict, identificador: str) -> dict:
    resposta = client.post("/comandas", headers=headers, json={"identificador": identificador})
    assert resposta.status_code == 201
    return resposta.json()


def test_v1_listar_comandas_respeita_limit(client: TestClient, headers_caixa: dict):
    for i in range(5):
        _abrir_comanda(client, headers_caixa, f"MESA {i}")

    resposta = client.get("/v1/comandas?limit=2", headers=headers_caixa)
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert len(corpo["items"]) == 2
    assert corpo["limit"] == 2
    assert corpo["offset"] == 0


def test_v1_listar_comandas_default_nao_estoura_com_muitos_registros(client: TestClient, headers_caixa: dict):
    for i in range(60):
        _abrir_comanda(client, headers_caixa, f"MESA {i}")

    resposta = client.get("/v1/comandas", headers=headers_caixa)
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert len(corpo["items"]) == 50
    assert corpo["total"] == 60


def test_v1_listar_comandas_total_reflete_contagem_real_nao_so_pagina_atual(client: TestClient, headers_caixa: dict):
    for i in range(7):
        _abrir_comanda(client, headers_caixa, f"MESA {i}")

    resposta = client.get("/v1/comandas?limit=3&offset=6", headers=headers_caixa)
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert len(corpo["items"]) == 1
    assert corpo["total"] == 7
    assert corpo["offset"] == 6


def test_v1_listar_comandas_rejeita_limit_acima_do_maximo(client: TestClient, headers_caixa: dict):
    resposta = client.get("/v1/comandas?limit=500", headers=headers_caixa)
    assert resposta.status_code == 422


def test_listar_comandas_sem_versao_continua_devolvendo_array_puro(client: TestClient, headers_caixa: dict):
    """Garante que a rota antiga (sem /v1) não virou breaking change."""
    _abrir_comanda(client, headers_caixa, "MESA 01")

    resposta = client.get("/comandas", headers=headers_caixa)
    assert resposta.status_code == 200
    assert isinstance(resposta.json(), list)
