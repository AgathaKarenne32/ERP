from fastapi.testclient import TestClient


def test_abrir_caixa_bloqueia_segundo_caixa_aberto(client: TestClient, headers_admin: dict):
    primeira = client.post("/caixa/abrir", headers=headers_admin)
    assert primeira.status_code == 201

    segunda = client.post("/caixa/abrir", headers=headers_admin)
    assert segunda.status_code == 409


def test_fechar_caixa_sem_caixa_aberto_bloqueia(client: TestClient, headers_admin: dict):
    resposta = client.patch("/caixa/fechar", headers=headers_admin)
    assert resposta.status_code == 409


def test_fechar_caixa_aberto_funciona(client: TestClient, headers_admin: dict):
    client.post("/caixa/abrir", headers=headers_admin)
    resposta = client.patch("/caixa/fechar", headers=headers_admin)
    assert resposta.status_code == 200
    assert resposta.json()["fechado_em"] is not None
