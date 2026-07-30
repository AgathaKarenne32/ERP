import uuid

from fastapi.testclient import TestClient


def test_cozinha_nao_pode_abrir_comanda(client: TestClient, headers_cozinha: dict):
    resposta = client.post("/comandas", headers=headers_cozinha, json={"identificador": "MESA 01"})
    assert resposta.status_code == 403


def test_garcom_pode_abrir_comanda(client: TestClient, headers_garcom: dict):
    resposta = client.post("/comandas", headers=headers_garcom, json={"identificador": "MESA 01"})
    assert resposta.status_code == 201


def test_cozinha_nao_pode_listar_comandas(client: TestClient, headers_cozinha: dict):
    resposta = client.get("/comandas", headers=headers_cozinha)
    assert resposta.status_code == 403


def test_cozinha_nao_pode_lancar_item(client: TestClient, headers_garcom: dict, headers_cozinha: dict):
    comanda = client.post("/comandas", headers=headers_garcom, json={"identificador": "MESA 01"}).json()

    resposta = client.post(
        f"/comandas/{comanda['id']}/itens",
        headers=headers_cozinha,
        json={
            "id_produto": str(uuid.uuid4()),
            "nome_produto": "Caipirinha",
            "quantidade": 1,
            "preco_aplicado": 15,
        },
    )
    assert resposta.status_code == 403


def test_cozinha_nao_pode_transferir_itens(client: TestClient, headers_garcom: dict, headers_cozinha: dict):
    origem = client.post("/comandas", headers=headers_garcom, json={"identificador": "MESA 01"}).json()
    destino = client.post("/comandas", headers=headers_garcom, json={"identificador": "MESA 02"}).json()

    resposta = client.post(
        f"/comandas/{origem['id']}/transferir-itens",
        headers=headers_cozinha,
        json={"id_comanda_destino": destino["id"], "id_itens": []},
    )
    assert resposta.status_code == 403


def test_cozinha_nao_pode_vincular_cliente(client: TestClient, headers_garcom: dict, headers_cozinha: dict):
    comanda = client.post("/comandas", headers=headers_garcom, json={"identificador": "MESA 01"}).json()

    resposta = client.patch(
        f"/comandas/{comanda['id']}/cliente",
        headers=headers_cozinha,
        json={"id_cliente": str(uuid.uuid4())},
    )
    assert resposta.status_code == 403


def test_caixa_nao_pode_atualizar_status_de_ticket(
    client: TestClient, headers_garcom: dict, headers_caixa: dict
):
    """CAIXA não tem papel na produção da cozinha; só COZINHA/GARCOM/ADMIN/GERENTE."""
    comanda = client.post("/comandas", headers=headers_garcom, json={"identificador": "MESA 01"}).json()
    item = client.post(
        f"/comandas/{comanda['id']}/itens",
        headers=headers_garcom,
        json={
            "id_produto": str(uuid.uuid4()),
            "nome_produto": "Caipirinha",
            "quantidade": 1,
            "preco_aplicado": 15,
        },
    ).json()
    ticket_id = client.get("/kds/fila", headers=headers_garcom).json()[0]["id"]

    resposta = client.patch(
        f"/kds/tickets/{ticket_id}",
        headers=headers_caixa,
        params={"novo_status": "EM_PREPARO"},
    )
    assert resposta.status_code == 403
    assert item["nome_produto"] == "Caipirinha"


def test_cozinha_pode_atualizar_status_de_ticket(client: TestClient, headers_garcom: dict, headers_cozinha: dict):
    comanda = client.post("/comandas", headers=headers_garcom, json={"identificador": "MESA 01"}).json()
    client.post(
        f"/comandas/{comanda['id']}/itens",
        headers=headers_garcom,
        json={
            "id_produto": str(uuid.uuid4()),
            "nome_produto": "Caipirinha",
            "quantidade": 1,
            "preco_aplicado": 15,
        },
    )
    ticket_id = client.get("/kds/fila", headers=headers_garcom).json()[0]["id"]

    resposta = client.patch(
        f"/kds/tickets/{ticket_id}",
        headers=headers_cozinha,
        params={"novo_status": "EM_PREPARO"},
    )
    assert resposta.status_code == 200
    assert resposta.json()["status_producao"] == "EM_PREPARO"


def test_garcom_nao_pode_ver_relatorio_de_vendas(client: TestClient, headers_garcom: dict):
    resposta = client.get("/relatorios/vendas", headers=headers_garcom)
    assert resposta.status_code == 403


def test_caixa_pode_ver_relatorio_de_vendas(client: TestClient, headers_caixa: dict):
    resposta = client.get("/relatorios/vendas", headers=headers_caixa)
    assert resposta.status_code == 200


def test_garcom_nao_pode_ver_produtos_mais_vendidos(client: TestClient, headers_garcom: dict):
    resposta = client.get("/relatorios/produtos-mais-vendidos", headers=headers_garcom)
    assert resposta.status_code == 403
