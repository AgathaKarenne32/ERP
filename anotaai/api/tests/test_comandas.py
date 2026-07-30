import uuid

from fastapi.testclient import TestClient


def _abrir_comanda(client: TestClient, headers: dict, identificador: str = "MESA 01") -> dict:
    resposta = client.post("/comandas", headers=headers, json={"identificador": identificador})
    assert resposta.status_code == 201
    return resposta.json()


def _lancar_item(client: TestClient, headers: dict, comanda_id: str, preco: float = 15.0) -> dict:
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


def test_garcom_nao_pode_fechar_comanda(client: TestClient, headers_garcom: dict):
    """RN03: só Caixa/Admin/Gerente fecham comanda."""
    comanda = _abrir_comanda(client, headers_garcom)
    resposta = client.patch(f"/comandas/{comanda['id']}/fechar", headers=headers_garcom)
    assert resposta.status_code == 403


def test_caixa_fecha_comanda(client: TestClient, headers_caixa: dict):
    comanda = _abrir_comanda(client, headers_caixa)
    resposta = client.patch(f"/comandas/{comanda['id']}/fechar", headers=headers_caixa)
    assert resposta.status_code == 200
    assert resposta.json()["status"] == "PAGA"


def test_nao_pode_lancar_item_em_comanda_fechada(client: TestClient, headers_caixa: dict):
    """RN03."""
    comanda = _abrir_comanda(client, headers_caixa)
    client.patch(f"/comandas/{comanda['id']}/fechar", headers=headers_caixa)

    resposta = client.post(
        f"/comandas/{comanda['id']}/itens",
        headers=headers_caixa,
        json={
            "id_produto": str(uuid.uuid4()),
            "nome_produto": "Caipirinha",
            "quantidade": 1,
            "preco_aplicado": 15,
        },
    )
    assert resposta.status_code == 409


def test_item_grava_snapshot_de_preco_e_nome(client: TestClient, headers_caixa: dict):
    """RN04: preço e nome são imutáveis a partir da gravação (snapshot)."""
    comanda = _abrir_comanda(client, headers_caixa)
    item = _lancar_item(client, headers_caixa, comanda["id"], preco=15.0)

    assert item["preco_aplicado"] == 15.0
    assert item["nome_produto"] == "Caipirinha"


def test_cancelar_comanda_ja_paga_bloqueia(client: TestClient, headers_caixa: dict):
    """RN03 (extensão)."""
    comanda = _abrir_comanda(client, headers_caixa)
    client.patch(f"/comandas/{comanda['id']}/fechar", headers=headers_caixa)

    resposta = client.patch(
        f"/comandas/{comanda['id']}/cancelar", headers=headers_caixa, json={"motivo": "teste"}
    )
    assert resposta.status_code == 409


def test_transferir_itens_recalcula_totais(client: TestClient, headers_caixa: dict):
    """RF05, protege a mesma integridade financeira que a RN04 garante no item."""
    origem = _abrir_comanda(client, headers_caixa, "MESA 01")
    destino = _abrir_comanda(client, headers_caixa, "MESA 02")
    item = _lancar_item(client, headers_caixa, origem["id"], preco=15.0)

    resposta = client.post(
        f"/comandas/{origem['id']}/transferir-itens",
        headers=headers_caixa,
        json={"id_comanda_destino": destino["id"], "id_itens": [item["id"]]},
    )
    assert resposta.status_code == 200
    assert resposta.json()["valor_total"] == 0.0

    comandas = client.get("/comandas", headers=headers_caixa).json()
    destino_final = next(c for c in comandas if c["id"] == destino["id"])
    assert destino_final["valor_total"] == 15.0


def test_ingestao_externa_e_idempotente(client: TestClient, headers_interno: dict, loja_inicializada: None):
    """Reenvio do mesmo pedido externo (retry de webhook do provedor) nao
    duplica a comanda."""
    payload = {
        "origem": "IFOOD",
        "id_referencia_externa": "TESTE-IDEMPOTENCIA-001",
        "itens": [
            {
                "id_produto": str(uuid.uuid4()),
                "nome_produto": "Caipirinha",
                "quantidade": 1,
                "preco_aplicado": 15,
            }
        ],
    }

    primeira = client.post("/comandas/ingestao-externa", headers=headers_interno, json=payload)
    assert primeira.status_code == 201

    segunda = client.post("/comandas/ingestao-externa", headers=headers_interno, json=payload)
    assert segunda.status_code == 200
    assert segunda.json()["id"] == primeira.json()["id"]
