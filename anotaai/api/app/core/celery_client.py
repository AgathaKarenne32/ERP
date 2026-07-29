from celery import Celery

from .config import settings

celery_client = Celery("anotaai_api_producer", broker=settings.celery_broker_url)
