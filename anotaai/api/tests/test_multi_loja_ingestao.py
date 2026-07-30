import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import IntegracaoLoja, OrigemPedido


def _payload_ifood(identificador_loja_externa: str, referencia: str) -> dict:
    return {
        "origem": "IFOOD",
        "identificador_loja_externa": identificador_loja_externa,
        "id_referencia_externa": referencia,
        "itens": [
            {
                "id_produto": str(uuid.uuid4()),
                "nome_produto": "Caipirinha",
                "quantidade": 1,
                "preco_aplicado": 15,
            }
        ],
    }


def test_ingestao_externa_sem_mapeamento_retorna_erro_claro(client: TestClient, headers_interno: dict):
    resposta = client.post(
        "/comandas/ingestao-externa",
        headers=headers_interno,
        json=_payload_ifood("MERCHANT-INEXISTENTE", "REF-001"),
    )
    assert resposta.status_code == 422


def test_ingestao_externa_roteia_para_loja_correta_por_identificador(
    client: TestClient, session: Session, headers_interno: dict
):
    loja_a = uuid.uuid4()
    loja_b = uuid.uuid4()
    session.add(IntegracaoLoja(id_loja=loja_a, provedor=OrigemPedido.IFOOD, identificador_externo="MERCHANT-A"))
    session.add(IntegracaoLoja(id_loja=loja_b, provedor=OrigemPedido.IFOOD, identificador_externo="MERCHANT-B"))
    session.commit()

    resposta_a = client.post(
        "/comandas/ingestao-externa", headers=headers_interno, json=_payload_ifood("MERCHANT-A", "REF-A")
    )
    resposta_b = client.post(
        "/comandas/ingestao-externa", headers=headers_interno, json=_payload_ifood("MERCHANT-B", "REF-B")
    )

    assert resposta_a.status_code == 201
    assert resposta_b.status_code == 201

    # Isolamento é verificado direto no banco: listar via /comandas exigiria
    # o JWT de um operador de uma loja específica, o que não é o foco aqui.
    from app.models import Comanda

    comanda_a = session.get(Comanda, uuid.UUID(resposta_a.json()["id"]))
    comanda_b = session.get(Comanda, uuid.UUID(resposta_b.json()["id"]))
    assert comanda_a.id_loja == loja_a
    assert comanda_b.id_loja == loja_b
    assert comanda_a.id_loja != comanda_b.id_loja


def test_ingestao_externa_nao_pega_loja_arbitraria_com_duas_lojas_cadastradas(
    client: TestClient, session: Session, headers_interno: dict
):
    """Regressão do bug original: a versão antiga fazia
    select(Operador).first() e pegava a loja do primeiro operador
    cadastrado, ignorando qual loja o pedido realmente era."""
    from app.core.security import hash_password
    from app.models import Comanda, Operador, PapelOperador

    loja_antiga = uuid.uuid4()
    loja_pedido = uuid.uuid4()

    # Operador da loja_antiga é criado primeiro — no bug original, seria
    # essa loja escolhida indevidamente pra QUALQUER pedido externo.
    session.add(
        Operador(
            id_loja=loja_antiga,
            nome="Admin Antigo",
            email="antigo@teste.local",
            senha_hash=hash_password("senha123"),
            papel=PapelOperador.ADMIN,
        )
    )
    session.add(
        IntegracaoLoja(id_loja=loja_pedido, provedor=OrigemPedido.IFOOD, identificador_externo="MERCHANT-PEDIDO")
    )
    session.commit()

    resposta = client.post(
        "/comandas/ingestao-externa", headers=headers_interno, json=_payload_ifood("MERCHANT-PEDIDO", "REF-XYZ")
    )
    assert resposta.status_code == 201

    comanda = session.get(Comanda, uuid.UUID(resposta.json()["id"]))
    assert comanda.id_loja == loja_pedido
    assert comanda.id_loja != loja_antiga


def test_criar_integracao_exige_admin(client: TestClient, headers_garcom: dict):
    resposta = client.post(
        "/integracoes",
        headers=headers_garcom,
        json={"provedor": "IFOOD", "identificador_externo": "MERCHANT-X"},
    )
    assert resposta.status_code == 403


def test_criar_integracao_admin_sucesso(client: TestClient, headers_admin: dict):
    resposta = client.post(
        "/integracoes",
        headers=headers_admin,
        json={"provedor": "IFOOD", "identificador_externo": "MERCHANT-X"},
    )
    assert resposta.status_code == 201
    assert resposta.json()["identificador_externo"] == "MERCHANT-X"


def test_criar_integracao_duplicada_retorna_409(client: TestClient, headers_admin: dict):
    payload = {"provedor": "IFOOD", "identificador_externo": "MERCHANT-DUP"}
    primeira = client.post("/integracoes", headers=headers_admin, json=payload)
    segunda = client.post("/integracoes", headers=headers_admin, json=payload)
    assert primeira.status_code == 201
    assert segunda.status_code == 409


def test_listar_integracoes_retorna_apenas_da_loja_do_operador(
    client: TestClient, headers_admin: dict
):
    client.post("/integracoes", headers=headers_admin, json={"provedor": "IFOOD", "identificador_externo": "M1"})
    resposta = client.get("/integracoes", headers=headers_admin)
    assert resposta.status_code == 200
    assert len(resposta.json()) == 1
