import os

from celery import Celery

broker_url = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
backend_url = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1")

celery_app = Celery("anotaai_worker", broker=broker_url, backend=backend_url)
celery_app.conf.task_routes = {"app.tasks.*": {"queue": "integracoes"}}
