import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models import StatusProducao, TicketProducao


def _abrir_comanda(client: TestClient, headers: dict) -> dict:
    resposta = client.post("/comandas", headers=headers, json={"identificador": "MESA 01"})
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


def test_remove_item_de_comanda_aberta_recalcula_total(client: TestClient, headers_caixa: dict):
    comanda = _abrir_comanda(client, headers_caixa)
    item = _lancar_item(client, headers_caixa, comanda["id"], preco=15.0)

    resposta = client.delete(f"/comandas/{comanda['id']}/itens/{item['id']}", headers=headers_caixa)
    assert resposta.status_code == 204

    comandas = client.get("/comandas", headers=headers_caixa).json()
    comanda_atualizada = next(c for c in comandas if c["id"] == comanda["id"])
    assert comanda_atualizada["valor_total"] == 0.0


def test_bloqueia_remocao_de_item_de_comanda_fechada(client: TestClient, headers_caixa: dict):
    comanda = _abrir_comanda(client, headers_caixa)
    item = _lancar_item(client, headers_caixa, comanda["id"])
    client.patch(
        f"/comandas/{comanda['id']}/fechar",
        headers=headers_caixa,
        json={"forma_pagamento": "DINHEIRO"},
    )

    resposta = client.delete(f"/comandas/{comanda['id']}/itens/{item['id']}", headers=headers_caixa)
    assert resposta.status_code == 409


def test_bloqueia_remocao_de_item_ja_em_preparo(
    client: TestClient, session: Session, headers_caixa: dict
):
    comanda = _abrir_comanda(client, headers_caixa)
    item = _lancar_item(client, headers_caixa, comanda["id"])

    ticket = session.exec(
        select(TicketProducao).where(TicketProducao.id_item_comanda == uuid.UUID(item["id"]))
    ).first()
    ticket.status_producao = StatusProducao.EM_PREPARO
    session.add(ticket)
    session.commit()

    resposta = client.delete(f"/comandas/{comanda['id']}/itens/{item['id']}", headers=headers_caixa)
    assert resposta.status_code == 409

    comandas = client.get("/comandas", headers=headers_caixa).json()
    comanda_atualizada = next(c for c in comandas if c["id"] == comanda["id"])
    assert comanda_atualizada["valor_total"] == 15.0


def test_remover_item_inexistente_retorna_404(client: TestClient, headers_caixa: dict):
    comanda = _abrir_comanda(client, headers_caixa)

    resposta = client.delete(f"/comandas/{comanda['id']}/itens/{uuid.uuid4()}", headers=headers_caixa)
    assert resposta.status_code == 404
