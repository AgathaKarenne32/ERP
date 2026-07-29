import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from prometheus_fastapi_instrumentator import Instrumentator

from .core.logging_config import configurar_logging
from .routers import auth, caixa, clientes, insumos, lojas, produtos, vendas
from .seed import seed_demo_data

configurar_logging("ecletica-api")
logger = logging.getLogger("app.access")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    seed_demo_data()
    yield


app = FastAPI(title="Eclética API", version="0.1.0", lifespan=lifespan)

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
    return {"status": "ok", "service": "ecletica-api"}


app.include_router(auth.router)
app.include_router(produtos.router)
app.include_router(insumos.router)
app.include_router(clientes.router)
app.include_router(vendas.router)
app.include_router(caixa.router)
app.include_router(lojas.router)
