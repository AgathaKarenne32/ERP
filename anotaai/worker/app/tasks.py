"""Tasks de integração omnichannel (RF01, RF06 e RNF03 do plano).

Nesta fase (Fase 0 — fundação) estas tasks são stubs: apenas normalizam o
payload recebido do provedor externo para o formato definido em
docs/api-contracts.md e logam o resultado. A publicação do evento para a
anotaai-api (fila -> POST /comandas/{id}/itens) entra na Fase 3 do plano,
junto com a integração real com WhatsApp (Meta Cloud API) e iFood.
"""

import logging

from .celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.processar_webhook_ifood")
def processar_webhook_ifood(payload: dict) -> dict:
    evento_normalizado = {
        "evento": "NOVO_PEDIDO",
        "detalhes_pedido": {
            "origem_pedido": "IFOOD",
            "id_referencia_externa": payload.get("id"),
        },
        "itens": payload.get("items", []),
    }
    logger.info("Webhook iFood normalizado: %s", evento_normalizado)
    return evento_normalizado


@celery_app.task(name="app.tasks.processar_webhook_whatsapp")
def processar_webhook_whatsapp(payload: dict) -> dict:
    evento_normalizado = {
        "evento": "NOVO_PEDIDO",
        "detalhes_pedido": {
            "origem_pedido": "WHATSAPP",
            "identificador_cliente": payload.get("from"),
        },
        "itens": payload.get("itens", []),
    }
    logger.info("Webhook WhatsApp normalizado: %s", evento_normalizado)
    return evento_normalizado
