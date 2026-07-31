import uuid

from fastapi.testclient import TestClient

from app.models import ItemComanda


def _abrir_comanda(client: TestClient, headers: dict) -> dict:
    resposta = client.post("/comandas", headers=headers, json={"identificador": "MESA 01"})
    assert resposta.status_code == 201
    return resposta.json()


def _lancar_item(client: TestClient, headers: dict, comanda_id: str, preco: float) -> dict:
    resposta = client.post(
        f"/comandas/{comanda_id}/itens",
        headers=headers,
        json={
            "id_produto": str(uuid.uuid4()),
            "nome_produto": "Caipirinha",
            "quantidade": 1,
            "preco_aplicado": preco,
        },
    )
    assert resposta.status_code == 201
    return resposta.json()


def test_aplicar_desconto_exige_papel_restrito(client: TestClient, headers_garcom: dict):
    comanda = _abrir_comanda(client, headers_garcom)

    resposta = client.patch(
        f"/comandas/{comanda['id']}/desconto",
        headers=headers_garcom,
        json={"desconto_total": 5.0},
    )
    assert resposta.status_code == 403


def test_aplicar_desconto_atualiza_valor_liquido(client: TestClient, headers_caixa: dict):
    comanda = _abrir_comanda(client, headers_caixa)
    _lancar_item(client, headers_caixa, comanda["id"], preco=100.0)

    resposta = client.patch(
        f"/comandas/{comanda['id']}/desconto",
        headers=headers_caixa,
        json={"desconto_total": 20.0},
    )
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["valor_total"] == 100.0
    assert corpo["desconto_total"] == 20.0
    assert corpo["valor_liquido"] == 80.0


def test_desconto_nao_afeta_preco_aplicado_dos_itens(client: TestClient, session, headers_caixa: dict):
    comanda = _abrir_comanda(client, headers_caixa)
    item = _lancar_item(client, headers_caixa, comanda["id"], preco=50.0)

    resposta = client.patch(
        f"/comandas/{comanda['id']}/desconto",
        headers=headers_caixa,
        json={"desconto_total": 10.0},
    )
    assert resposta.status_code == 200

    item_db = session.get(ItemComanda, uuid.UUID(item["id"]))
    assert item_db.preco_aplicado == 50.0
    assert item_db.nome_produto == "Caipirinha"


def test_desconto_maior_que_valor_total_e_rejeitado(client: TestClient, headers_caixa: dict):
    comanda = _abrir_comanda(client, headers_caixa)
    _lancar_item(client, headers_caixa, comanda["id"], preco=30.0)

    resposta = client.patch(
        f"/comandas/{comanda['id']}/desconto",
        headers=headers_caixa,
        json={"desconto_total": 30.01},
    )
    assert resposta.status_code == 400


def test_desconto_negativo_e_rejeitado(client: TestClient, headers_caixa: dict):
    comanda = _abrir_comanda(client, headers_caixa)

    resposta = client.patch(
        f"/comandas/{comanda['id']}/desconto",
        headers=headers_caixa,
        json={"desconto_total": -1.0},
    )
    assert resposta.status_code == 422


def test_desconto_em_comanda_fechada_e_rejeitado(client: TestClient, headers_caixa: dict):
    comanda = _abrir_comanda(client, headers_caixa)
    client.patch(
        f"/comandas/{comanda['id']}/fechar",
        headers=headers_caixa,
        json={"forma_pagamento": "DINHEIRO"},
    )

    resposta = client.patch(
        f"/comandas/{comanda['id']}/desconto",
        headers=headers_caixa,
        json={"desconto_total": 1.0},
    )
    assert resposta.status_code == 409


def test_fechar_comanda_com_desconto_soma_valor_liquido_no_caixa(
    client: TestClient, headers_caixa: dict, monkeypatch
):
    chamadas = []
    monkeypatch.setattr(
        "app.routers.comandas.solicitar_baixa_estoque",
        lambda **kwargs: chamadas.append(kwargs),
    )

    comanda = _abrir_comanda(client, headers_caixa)
    _lancar_item(client, headers_caixa, comanda["id"], preco=100.0)

    resposta = client.patch(
        f"/comandas/{comanda['id']}/desconto",
        headers=headers_caixa,
        json={"desconto_total": 25.0},
    )
    assert resposta.status_code == 200

    resposta = client.patch(
        f"/comandas/{comanda['id']}/fechar",
        headers=headers_caixa,
        json={"forma_pagamento": "DINHEIRO"},
    )
    assert resposta.status_code == 200

    assert len(chamadas) == 1
    assert chamadas[0]["valor_total"] == 75.0


def test_relatorio_vendas_reflete_valor_liquido_com_desconto(client: TestClient, headers_caixa: dict):
    comanda = _abrir_comanda(client, headers_caixa)
    _lancar_item(client, headers_caixa, comanda["id"], preco=100.0)
    client.patch(
        f"/comandas/{comanda['id']}/desconto",
        headers=headers_caixa,
        json={"desconto_total": 25.0},
    )
    resposta = client.patch(
        f"/comandas/{comanda['id']}/fechar",
        headers=headers_caixa,
        json={"forma_pagamento": "DINHEIRO"},
    )
    assert resposta.status_code == 200

    resposta = client.get("/relatorios/vendas", headers=headers_caixa)
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["total_vendas"] == 75.0
    assert corpo["por_forma_pagamento"][0]["valor_total"] == 75.0
