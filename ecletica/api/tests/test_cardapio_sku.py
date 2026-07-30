from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import Loja, MapeamentoSkuExterno, Produto, ProvedorExterno


def _criar_produto(session: Session, loja: Loja, nome: str = "Caipirinha", ativo_venda: bool = True) -> Produto:
    produto = Produto(id_loja=loja.id, nome=nome, preco_venda=15, ativo_venda=ativo_venda)
    session.add(produto)
    session.commit()
    session.refresh(produto)
    return produto


def test_mapear_sku_admin_sucesso(client: TestClient, session: Session, loja: Loja, headers_admin: dict):
    produto = _criar_produto(session, loja)

    resposta = client.post(
        f"/produtos/{produto.id}/mapear-sku",
        headers=headers_admin,
        json={"provedor": "IFOOD", "sku_externo": "SKU-IFOOD-1"},
    )

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["id_produto"] == str(produto.id)
    assert corpo["provedor"] == "IFOOD"
    assert corpo["sku_externo"] == "SKU-IFOOD-1"


def test_mapear_sku_exige_admin_ou_gerente(client: TestClient, session: Session, loja: Loja, headers_caixa: dict):
    produto = _criar_produto(session, loja)

    resposta = client.post(
        f"/produtos/{produto.id}/mapear-sku",
        headers=headers_caixa,
        json={"provedor": "IFOOD", "sku_externo": "SKU-IFOOD-1"},
    )

    assert resposta.status_code == 403


def test_mapear_sku_produto_de_outra_loja_retorna_404(client: TestClient, session: Session, headers_admin: dict):
    outra_loja = Loja(nome="Outra Loja", cnpj="11.111.111/0001-11")
    session.add(outra_loja)
    session.commit()
    session.refresh(outra_loja)
    produto = _criar_produto(session, outra_loja)

    resposta = client.post(
        f"/produtos/{produto.id}/mapear-sku",
        headers=headers_admin,
        json={"provedor": "IFOOD", "sku_externo": "SKU-IFOOD-1"},
    )

    assert resposta.status_code == 404


def test_mapear_sku_duplicado_retorna_409(client: TestClient, session: Session, loja: Loja, headers_admin: dict):
    produto_a = _criar_produto(session, loja, nome="Caipirinha")
    produto_b = _criar_produto(session, loja, nome="Mojito")
    payload = {"provedor": "IFOOD", "sku_externo": "SKU-DUP"}

    primeira = client.post(f"/produtos/{produto_a.id}/mapear-sku", headers=headers_admin, json=payload)
    segunda = client.post(f"/produtos/{produto_b.id}/mapear-sku", headers=headers_admin, json=payload)

    assert primeira.status_code == 201
    assert segunda.status_code == 409


def test_resolver_sku_sucesso(client: TestClient, session: Session, loja: Loja, headers_interno: dict):
    produto = _criar_produto(session, loja)
    session.add(MapeamentoSkuExterno(id_produto=produto.id, provedor=ProvedorExterno.IFOOD, sku_externo="SKU-1"))
    session.commit()

    resposta = client.get(
        "/produtos/resolver-sku",
        headers=headers_interno,
        params={"provedor": "IFOOD", "sku_externo": "SKU-1"},
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["id"] == str(produto.id)
    assert corpo["nome"] == "Caipirinha"


def test_resolver_sku_nao_mapeado_retorna_404(client: TestClient, headers_interno: dict):
    resposta = client.get(
        "/produtos/resolver-sku",
        headers=headers_interno,
        params={"provedor": "IFOOD", "sku_externo": "SKU-INEXISTENTE"},
    )

    assert resposta.status_code == 404


def test_resolver_sku_exige_token_interno(client: TestClient):
    resposta = client.get("/produtos/resolver-sku", params={"provedor": "IFOOD", "sku_externo": "SKU-1"})
    assert resposta.status_code == 422


def test_cardapio_publico_lista_apenas_ativos(client: TestClient, session: Session, loja: Loja):
    ativo = _criar_produto(session, loja, nome="Caipirinha", ativo_venda=True)
    _criar_produto(session, loja, nome="Fora de linha", ativo_venda=False)

    resposta = client.get("/cardapio", params={"id_loja": str(loja.id)})

    assert resposta.status_code == 200
    nomes = [item["nome"] for item in resposta.json()]
    assert nomes == ["Caipirinha"]
    assert resposta.json()[0]["id"] == str(ativo.id)


def test_cardapio_nao_lista_produto_de_outra_loja(client: TestClient, session: Session, loja: Loja):
    outra_loja = Loja(nome="Outra Loja", cnpj="22.222.222/0001-22")
    session.add(outra_loja)
    session.commit()
    session.refresh(outra_loja)
    _criar_produto(session, outra_loja, nome="Produto de outra loja")

    resposta = client.get("/cardapio", params={"id_loja": str(loja.id)})

    assert resposta.status_code == 200
    assert resposta.json() == []
