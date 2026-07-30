from fastapi.testclient import TestClient


def test_garcom_nao_pode_cadastrar_cliente(client: TestClient, headers_garcom: dict):
    resposta = client.post(
        "/clientes",
        headers=headers_garcom,
        json={"nome": "Maria", "cpf": "111.222.333-44"},
    )
    assert resposta.status_code == 403


def test_caixa_pode_cadastrar_cliente(client: TestClient, headers_caixa: dict):
    resposta = client.post(
        "/clientes",
        headers=headers_caixa,
        json={"nome": "Maria", "cpf": "111.222.333-44"},
    )
    assert resposta.status_code == 201


def test_qualquer_papel_autenticado_lista_clientes(client: TestClient, headers_garcom: dict):
    """Leitura operacional (consulta de fidelidade em atendimento) fica aberta
    a qualquer papel autenticado — só o cadastro é restrito."""
    resposta = client.get("/clientes", headers=headers_garcom)
    assert resposta.status_code == 200


def test_garcom_nao_pode_listar_caixas(client: TestClient, headers_garcom: dict):
    resposta = client.get("/caixa", headers=headers_garcom)
    assert resposta.status_code == 403


def test_caixa_pode_listar_caixas(client: TestClient, headers_caixa: dict):
    resposta = client.get("/caixa", headers=headers_caixa)
    assert resposta.status_code == 200
