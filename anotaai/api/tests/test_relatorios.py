import uuid

from fastapi.testclient import TestClient


def _abrir_e_fechar_comanda(client: TestClient, headers: dict, forma_pagamento: str, preco: float) -> dict:
    comanda = client.post("/comandas", headers=headers, json={"identificador": "MESA 01"}).json()
    client.post(
        f"/comandas/{comanda['id']}/itens",
        headers=headers,
        json={
            "id_produto": str(uuid.uuid4()),
            "nome_produto": "Caipirinha",
            "quantidade": 1,
            "preco_aplicado": preco,
        },
    )
    resposta = client.patch(
        f"/comandas/{comanda['id']}/fechar",
        headers=headers,
        json={"forma_pagamento": forma_pagamento},
    )
    assert resposta.status_code == 200
    return resposta.json()


def test_relatorio_vendas_agrupa_por_forma_pagamento(client: TestClient, headers_caixa: dict):
    _abrir_e_fechar_comanda(client, headers_caixa, "DINHEIRO", preco=15.0)
    _abrir_e_fechar_comanda(client, headers_caixa, "PIX", preco=20.0)
    _abrir_e_fechar_comanda(client, headers_caixa, "PIX", preco=10.0)

    resposta = client.get("/relatorios/vendas", headers=headers_caixa)
    assert resposta.status_code == 200
    corpo = resposta.json()

    assert corpo["quantidade_comandas"] == 3
    assert corpo["total_vendas"] == 45.0

    por_forma = {item["forma_pagamento"]: item for item in corpo["por_forma_pagamento"]}
    assert por_forma["DINHEIRO"]["valor_total"] == 15.0
    assert por_forma["DINHEIRO"]["quantidade_comandas"] == 1
    assert por_forma["PIX"]["valor_total"] == 30.0
    assert por_forma["PIX"]["quantidade_comandas"] == 2
