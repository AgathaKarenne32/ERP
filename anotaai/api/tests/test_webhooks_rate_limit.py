import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


@pytest.fixture
def mock_celery():
    """Mock the Celery client to avoid needing Redis."""
    with patch("app.routers.webhooks.celery_client") as mock:
        yield mock


def test_webhook_ifood_rate_limiting(mock_celery):
    """Test that iFood webhook is rate limited to 30 requests per minute per IP."""
    client = TestClient(app)

    responses = []
    for i in range(31):
        payload = {"order": f"test_{i}"}
        corpo = json.dumps(payload).encode()

        import hashlib
        import hmac

        assinatura = hmac.new(
            settings.ifood_webhook_secret.encode(), corpo, hashlib.sha256
        ).hexdigest()

        response = client.post(
            "/webhooks/ifood",
            content=corpo,
            headers={
                "x-ifood-signature": assinatura,
                "X-Forwarded-For": "127.0.0.1",
            },
        )
        responses.append(response.status_code)

    assert responses[:30] == [202] * 30
    assert responses[30] == 429


def test_webhook_whatsapp_post_rate_limiting(mock_celery):
    """Test that WhatsApp webhook POST is rate limited to 30 requests per minute per IP."""
    client = TestClient(app)

    responses = []
    for i in range(31):
        payload = {"message": f"test_{i}"}
        corpo = json.dumps(payload).encode()

        import hashlib
        import hmac

        assinatura = "sha256=" + hmac.new(
            settings.meta_app_secret.encode(), corpo, hashlib.sha256
        ).hexdigest()

        response = client.post(
            "/webhooks/whatsapp",
            content=corpo,
            headers={
                "x-hub-signature-256": assinatura,
                "X-Forwarded-For": "127.0.0.1",
            },
        )
        responses.append(response.status_code)

    assert responses[:30] == [202] * 30
    assert responses[30] == 429


def test_webhook_whatsapp_get_rate_limiting():
    """Test that WhatsApp verification GET is rate limited to 10 requests per minute per IP."""
    client = TestClient(app)

    responses = []
    for i in range(11):
        response = client.get(
            "/webhooks/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": settings.meta_verify_token,
                "hub.challenge": "test_challenge",
            },
            headers={"X-Forwarded-For": "127.0.0.1"},
        )
        responses.append(response.status_code)

    assert responses[:10] == [200] * 10
    assert responses[10] == 429
