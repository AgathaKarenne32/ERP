from fastapi.testclient import TestClient


def _criar_insumo(client: TestClient, headers: dict, nome: str, qtd_estoque: float, estoque_minimo: float) -> dict:
    resposta = client.post(
        "/insumos",
        headers=headers,
        json={
            "nome": nome,
            "unidade_medida": "UN",
            "custo_unitario": 1.0,
            "qtd_estoque": qtd_estoque,
            "estoque_minimo": estoque_minimo,
        },
    )
    assert resposta.status_code == 201
    return resposta.json()


def test_lista_insumos_abaixo_do_minimo(client: TestClient, headers_admin: dict):
    _criar_insumo(client, headers_admin, "Gelo", qtd_estoque=5, estoque_minimo=10)
    _criar_insumo(client, headers_admin, "Limão", qtd_estoque=50, estoque_minimo=10)

    resposta = client.get("/insumos/abaixo-do-minimo", headers=headers_admin)
    assert resposta.status_code == 200
    nomes = [i["nome"] for i in resposta.json()]
    assert nomes == ["Gelo"]


def test_insumo_no_minimo_exato_nao_aparece_na_lista(client: TestClient, headers_admin: dict):
    _criar_insumo(client, headers_admin, "Gelo", qtd_estoque=10, estoque_minimo=10)

    resposta = client.get("/insumos/abaixo-do-minimo", headers=headers_admin)
    assert resposta.status_code == 200
    assert resposta.json() == []


def test_insumos_abaixo_do_minimo_exige_papel_restrito(client: TestClient, headers_caixa: dict):
    resposta = client.get("/insumos/abaixo-do-minimo", headers=headers_caixa)
    assert resposta.status_code == 403
