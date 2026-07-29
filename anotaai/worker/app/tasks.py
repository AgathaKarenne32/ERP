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
INTERNAL_API_TOKEN = os.getenv("INTERNAL_API_TOKEN", "change-me-internal-token")


def _injetar_comanda(origem: str, id_referencia_externa: str, itens: list[dict]) -> None:
    payload = {
        "origem": origem,
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


def _normalizar_itens(items_originais: list[dict]) -> list[dict]:
    """Mapeia os campos do payload do provedor pro formato interno.

    TODO (fora do escopo desta feature): assume que `id_produto` já vem no
    payload. Num catálogo real, o provedor referencia produtos pelo próprio
    SKU dele, e precisaríamos de uma tabela de-para (SKU externo ->
    id_produto da ecletica-api) — isso é o cardápio digital, Fase 3."""
    return [
        {
            "id_produto": item["id_produto"],
            "nome_produto": item.get("nome_produto") or item.get("name", "Item"),
            "quantidade": item.get("quantidade") or item.get("quantity", 1),
            "preco_aplicado": item.get("preco_aplicado") or item.get("price", 0),
        }
        for item in items_originais
    ]


@celery_app.task(
    name="app.tasks.processar_webhook_ifood",
    autoretry_for=(httpx.HTTPError,),
    retry_backoff=True,
    max_retries=3,
)
def processar_webhook_ifood(payload: dict) -> dict:
    id_referencia = str(payload.get("id"))
    itens = _normalizar_itens(payload.get("items", []))

    _injetar_comanda("IFOOD", id_referencia, itens)

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
    itens = _normalizar_itens(payload.get("itens", []))

    _injetar_comanda("WHATSAPP", id_referencia, itens)

    logger.info("Pedido WhatsApp de %s injetado como comanda", id_referencia)
    return {"status": "processado", "id_referencia_externa": id_referencia}
