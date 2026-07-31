from fastapi.testclient import TestClient


def _cadastrar_cliente(client: TestClient, headers: dict, nome: str) -> dict:
    resposta = client.post("/clientes", headers=headers, json={"nome": nome, "cpf": "000.000.000-00"})
    assert resposta.status_code == 201
    return resposta.json()


def test_v1_listar_clientes_respeita_limit(client: TestClient, headers_caixa: dict):
    for i in range(5):
        _cadastrar_cliente(client, headers_caixa, f"Cliente {i}")

    resposta = client.get("/v1/clientes?limit=2", headers=headers_caixa)
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert len(corpo["items"]) == 2
    assert corpo["limit"] == 2
    assert corpo["offset"] == 0


def test_v1_listar_clientes_default_nao_estoura_com_muitos_registros(client: TestClient, headers_caixa: dict):
    for i in range(60):
        _cadastrar_cliente(client, headers_caixa, f"Cliente {i:02d}")

    resposta = client.get("/v1/clientes", headers=headers_caixa)
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert len(corpo["items"]) == 50
    assert corpo["total"] == 60


def test_v1_listar_clientes_total_reflete_contagem_real_nao_so_pagina_atual(client: TestClient, headers_caixa: dict):
    for i in range(7):
        _cadastrar_cliente(client, headers_caixa, f"Cliente {i}")

    resposta = client.get("/v1/clientes?limit=3&offset=6", headers=headers_caixa)
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert len(corpo["items"]) == 1
    assert corpo["total"] == 7
    assert corpo["offset"] == 6


def test_listar_clientes_sem_versao_continua_devolvendo_array_puro(client: TestClient, headers_caixa: dict):
    """Garante que a rota antiga (sem /v1) não virou breaking change."""
    _cadastrar_cliente(client, headers_caixa, "Cliente Teste")

    resposta = client.get("/clientes", headers=headers_caixa)
    assert resposta.status_code == 200
    assert isinstance(resposta.json(), list)
