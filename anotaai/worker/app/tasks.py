"""Tasks de integração omnichannel (RF01, RF06 e RNF03 do plano).

A assinatura do provedor já foi validada na anotaai-api antes de a task
ser enfileirada. Aqui só normalizamos o payload pro formato interno e
injetamos a comanda de verdade via POST /comandas/ingestao-externa.
"""

import logging
import os

import httpx

from .celery_app import celery_app

logger = logging.getLogger(__name__)

ANOTAAI_API_URL = os.getenv("ANOTAAI_API_URL", "http://anotaai-api:8000")
ECLETICA_API_URL = os.getenv("ECLETICA_API_URL", "http://ecletica-api:8000")
INTERNAL_API_TOKEN = os.getenv("INTERNAL_API_TOKEN", "change-me-internal-token")


def _injetar_comanda(
    origem: str, identificador_loja_externa: str, id_referencia_externa: str, itens: list[dict]
) -> None:
    payload = {
        "origem": origem,
        "identificador_loja_externa": identificador_loja_externa,
        "id_referencia_externa": id_referencia_externa,
        "itens": itens,
    }
    headers = {"X-Internal-Token": INTERNAL_API_TOKEN}
    resposta = httpx.post(
        f"{ANOTAAI_API_URL}/comandas/ingestao-externa",
        json=payload,
        headers=headers,
        timeout=10.0,
    )
    resposta.raise_for_status()


def _resolver_produto(provedor: str, sku_externo: str) -> dict:
    """Traduz o SKU do provedor externo (cardápio digital dele) no produto
    real da ecletica-api, via o de-para cadastrado em /produtos/mapear-sku."""
    resposta = httpx.get(
        f"{ECLETICA_API_URL}/produtos/resolver-sku",
        params={"provedor": provedor, "sku_externo": sku_externo},
        headers={"X-Internal-Token": INTERNAL_API_TOKEN},
        timeout=5.0,
    )
    resposta.raise_for_status()
    return resposta.json()


def _normalizar_itens(provedor: str, items_originais: list[dict]) -> list[dict]:
    """Mapeia os campos do payload do provedor pro formato interno.

    O provedor referencia produtos pelo próprio SKU dele, não pelo
    id_produto da ecletica-api — por isso cada item precisa ser resolvido
    via o de-para (cardápio digital) antes de virar item de comanda."""
    itens = []
    for item in items_originais:
        sku_externo = str(item.get("sku_externo") or item.get("id"))
        produto = _resolver_produto(provedor, sku_externo)
        itens.append(
            {
                "id_produto": produto["id"],
                "nome_produto": item.get("nome_produto") or item.get("name") or produto["nome"],
                "quantidade": item.get("quantidade") or item.get("quantity", 1),
                "preco_aplicado": item.get("preco_aplicado") or item.get("price") or produto["preco_venda"],
            }
        )
    return itens


@celery_app.task(
    name="app.tasks.processar_webhook_ifood",
    autoretry_for=(httpx.HTTPError,),
    retry_backoff=True,
    max_retries=3,
)
def processar_webhook_ifood(payload: dict) -> dict:
    id_referencia = str(payload.get("id"))
    identificador_loja = str(payload.get("merchantId", ""))
    itens = _normalizar_itens("IFOOD", payload.get("items", []))

    _injetar_comanda("IFOOD", identificador_loja, id_referencia, itens)

    logger.info("Pedido iFood %s injetado como comanda", id_referencia)
    return {"status": "processado", "id_referencia_externa": id_referencia}


@celery_app.task(
    name="app.tasks.processar_webhook_whatsapp",
    autoretry_for=(httpx.HTTPError,),
    retry_backoff=True,
    max_retries=3,
)
def processar_webhook_whatsapp(payload: dict) -> dict:
    id_referencia = payload.get("from") or payload.get("identificador_cliente", "desconhecido")
    # "to" é o número do WhatsApp Business que recebeu a mensagem — é ele
    # que identifica QUAL loja, diferente de "from" (o cliente que pediu).
    identificador_loja = payload.get("to", "")
    itens = _normalizar_itens("WHATSAPP", payload.get("itens", []))

    _injetar_comanda("WHATSAPP", identificador_loja, id_referencia, itens)

    logger.info("Pedido WhatsApp de %s injetado como comanda", id_referencia)
    return {"status": "processado", "id_referencia_externa": id_referencia}
