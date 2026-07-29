from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import FichaTecnica, Insumo, Loja, Produto


def _criar_produto_com_ficha(session: Session, loja: Loja, qtd_utilizada: float = 2.0):
    insumo = Insumo(id_loja=loja.id, nome="Limão", unidade_medida="UN", custo_unitario=1.5, qtd_estoque=10)
    produto = Produto(id_loja=loja.id, nome="Caipirinha", preco_venda=15)
    session.add(insumo)
    session.add(produto)
    session.commit()
    session.refresh(insumo)
    session.refresh(produto)

    ficha = FichaTecnica(id_produto=produto.id, id_insumo=insumo.id, qtd_utilizada=qtd_utilizada)
    session.add(ficha)
    session.commit()
    return produto, insumo


def test_baixa_estoque_desconta_insumos_conforme_ficha_tecnica(
    client: TestClient, session: Session, loja: Loja, headers_interno: dict
):
    """RN01."""
    produto, insumo = _criar_produto_com_ficha(session, loja)

    resposta = client.post(
        "/vendas/baixa-estoque",
        headers=headers_interno,
        json={
            "id_loja": str(loja.id),
            "referencia": "teste-1",
            "valor_total": 15,
            "itens": [{"id_produto": str(produto.id), "quantidade": 1}],
        },
    )

    assert resposta.status_code == 204
    session.refresh(insumo)
    assert insumo.qtd_estoque == 8  # 10 - (1 * 2)


def test_baixa_estoque_bloqueia_se_insumo_insuficiente(
    client: TestClient, session: Session, loja: Loja, headers_interno: dict
):
    """RN02: nada é descontado se faltar qualquer insumo."""
    produto, insumo = _criar_produto_com_ficha(session, loja, qtd_utilizada=20)

    resposta = client.post(
        "/vendas/baixa-estoque",
        headers=headers_interno,
        json={
            "id_loja": str(loja.id),
            "referencia": "teste-2",
            "valor_total": 15,
            "itens": [{"id_produto": str(produto.id), "quantidade": 1}],
        },
    )

    assert resposta.status_code == 409
    session.refresh(insumo)
    assert insumo.qtd_estoque == 10


def test_baixa_estoque_exige_token_interno(client: TestClient, loja: Loja):
    resposta = client.post(
        "/vendas/baixa-estoque",
        json={"id_loja": str(loja.id), "itens": []},
    )
    assert resposta.status_code == 422  # header obrigatório ausente


def test_baixa_estoque_rejeita_token_interno_errado(client: TestClient, loja: Loja):
    resposta = client.post(
        "/vendas/baixa-estoque",
        headers={"X-Internal-Token": "token-errado"},
        json={"id_loja": str(loja.id), "itens": []},
    )
    assert resposta.status_code == 401
