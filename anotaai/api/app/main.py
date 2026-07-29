import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from .core.logging_config import configurar_logging
from .core.rate_limit import limiter
from .routers import auth, comandas, kds, relatorios, webhooks
from .seed import seed_demo_data

configurar_logging("anotaai-api")
logger = logging.getLogger("app.access")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    seed_demo_data()
    yield


app = FastAPI(title="AnotaAi-like API", version="0.1.0", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


@app.middleware("http")
async def log_requisicoes(request: Request, call_next):
    inicio = time.perf_counter()
    resposta = await call_next(request)
    duracao_ms = round((time.perf_counter() - inicio) * 1000, 2)
    logger.info(
        "request",
        extra={
            "http": {
                "method": request.method,
                "path": request.url.path,
                "status_code": resposta.status_code,
                "duration_ms": duracao_ms,
            }
        },
    )
    return resposta


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "anotaai-api"}


app.include_router(auth.router)
app.include_router(comandas.router)
app.include_router(kds.router)
app.include_router(relatorios.router)
app.include_router(webhooks.router)
