from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import Cliente, Loja


def test_creditar_pontos_soma_um_ponto_por_real(
    client: TestClient, session: Session, loja: Loja, headers_interno: dict
):
    """RN05: fidelidade só é creditada via esse endpoint, chamado após pagamento."""
    cliente = Cliente(id_loja=loja.id, nome="Maria", cpf="111.222.333-44")
    session.add(cliente)
    session.commit()
    session.refresh(cliente)

    resposta = client.post(
        f"/clientes/{cliente.id}/creditar-pontos",
        headers=headers_interno,
        json={"id_loja": str(loja.id), "valor_gasto": 37.90},
    )

    assert resposta.status_code == 200
    assert resposta.json()["pontos_fidelidade"] == 37


def test_creditar_pontos_acumula_entre_chamadas(
    client: TestClient, session: Session, loja: Loja, headers_interno: dict
):
    cliente = Cliente(id_loja=loja.id, nome="Maria", cpf="111.222.333-44")
    session.add(cliente)
    session.commit()
    session.refresh(cliente)

    client.post(
        f"/clientes/{cliente.id}/creditar-pontos",
        headers=headers_interno,
        json={"id_loja": str(loja.id), "valor_gasto": 10},
    )
    resposta = client.post(
        f"/clientes/{cliente.id}/creditar-pontos",
        headers=headers_interno,
        json={"id_loja": str(loja.id), "valor_gasto": 5},
    )

    assert resposta.json()["pontos_fidelidade"] == 15


def test_creditar_pontos_bloqueia_cliente_de_outra_loja(
    client: TestClient, session: Session, loja: Loja, headers_interno: dict
):
    """RN06: isolamento multi-loja — não pode creditar pontos num cliente
    que pertence a outra loja."""
    outra_loja = Loja(nome="Outra Loja", cnpj="11.111.111/0001-11")
    session.add(outra_loja)
    session.commit()
    session.refresh(outra_loja)

    cliente = Cliente(id_loja=loja.id, nome="Maria", cpf="111.222.333-44")
    session.add(cliente)
    session.commit()
    session.refresh(cliente)

    resposta = client.post(
        f"/clientes/{cliente.id}/creditar-pontos",
        headers=headers_interno,
        json={"id_loja": str(outra_loja.id), "valor_gasto": 10},
    )

    assert resposta.status_code == 404
