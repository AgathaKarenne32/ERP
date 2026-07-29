import json
import uuid

import redis
import redis.asyncio as redis_asyncio

from .config import settings

_redis_publicador = redis.Redis.from_url(settings.celery_broker_url)


def canal_kds(id_loja: uuid.UUID) -> str:
    return f"kds:{id_loja}"


def publicar_atualizacao_kds(id_loja: uuid.UUID, ticket_dict: dict) -> None:
    """Publica no Redis Pub/Sub pra alimentar o KDS em tempo real (RF07).
    Chamado sempre que um ticket muda de status ou um item novo é lançado."""
    _redis_publicador.publish(canal_kds(id_loja), json.dumps(ticket_dict))


def cliente_redis_async() -> redis_asyncio.Redis:
    return redis_asyncio.Redis.from_url(settings.celery_broker_url)
