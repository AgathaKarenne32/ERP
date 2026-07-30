import hashlib
import hmac
import json

from fastapi import APIRouter, HTTPException, Request, Response, status

from ..core.celery_client import celery_client
from ..core.config import settings
from ..core.rate_limit import limiter

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _assinatura_valida(segredo: str, corpo: bytes, assinatura_recebida: str) -> bool:
    assinatura_calculada = hmac.new(segredo.encode(), corpo, hashlib.sha256).hexdigest()
    return hmac.compare_digest(assinatura_calculada, assinatura_recebida)


@router.post("/ifood", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("30/minute")
async def webhook_ifood(request: Request) -> dict:
    """RF01: recebe pedidos do iFood. Valida a assinatura HMAC-SHA256 do
    corpo bruto antes de aceitar, e só enfileira — quem processa de fato
    é o anotaai-worker, de forma assíncrona (o webhook responde rápido,
    como os provedores exigem)."""
    corpo = await request.body()
    assinatura = request.headers.get("x-ifood-signature", "")

    if not _assinatura_valida(settings.ifood_webhook_secret, corpo, assinatura):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Assinatura inválida")

    payload = json.loads(corpo)
    celery_client.send_task("app.tasks.processar_webhook_ifood", args=[payload])
    return {"status": "recebido"}


@router.get("/whatsapp")
@limiter.limit("10/minute")
def verificar_whatsapp(request: Request) -> Response:
    """Handshake de verificação da Meta Cloud API: confirma o dono do
    endpoint respondendo o hub.challenge, só se o hub.verify_token bater
    com o segredo configurado no app da Meta."""
    modo = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge", "")

    if modo == "subscribe" and token == settings.meta_verify_token:
        return Response(content=challenge, media_type="text/plain")
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token de verificação inválido")


@router.post("/whatsapp", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("30/minute")
async def webhook_whatsapp(request: Request) -> dict:
    """RF01: recebe mensagens/pedidos do WhatsApp (Meta Cloud API). Valida
    a assinatura X-Hub-Signature-256 (HMAC-SHA256 com o app secret)."""
    corpo = await request.body()
    cabecalho = request.headers.get("x-hub-signature-256", "")
    assinatura = cabecalho.removeprefix("sha256=")

    if not _assinatura_valida(settings.meta_app_secret, corpo, assinatura):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Assinatura inválida")

    payload = json.loads(corpo)
    celery_client.send_task("app.tasks.processar_webhook_whatsapp", args=[payload])
    return {"status": "recebido"}
