import logging
import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text
from sqlmodel import Session

from .core.config import settings
from .core.db import get_session
from .core.logging_config import configurar_logging
from .core.rate_limit import limiter
from .routers import admin, auth, caixa, cardapio, clientes, insumos, lojas, produtos, vendas
from .seed import seed_demo_data

configurar_logging("ecletica-api")
logger = logging.getLogger("app.access")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    seed_demo_data()
    yield


app = FastAPI(title="Eclética API", version="0.1.0", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SlowAPIMiddleware)

Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


@app.middleware("http")
async def adicionar_security_headers(request: Request, call_next):
    resposta = await call_next(request)
    resposta.headers["X-Content-Type-Options"] = "nosniff"
    resposta.headers["X-Frame-Options"] = "DENY"
    resposta.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    resposta.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    resposta.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return resposta


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
    """Alias de /health/live, mantido por compatibilidade com quem já
    aponta pra este path."""
    return {"status": "ok", "service": "ecletica-api"}


@app.get("/health/live")
def health_live() -> dict:
    """Liveness: o processo está de pé. Nunca toca dependência externa —
    se isso falhar, é o processo em si que está travado/morto."""
    return {"status": "ok"}


@app.get("/health/ready")
def health_ready(session: Session = Depends(get_session)) -> dict:
    """Readiness: pronto pra receber tráfego real, ou seja, o banco responde.
    Postgres fora do ar não deve aparecer como 'saudável' aqui."""
    try:
        session.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Banco indisponível"
        ) from exc
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(produtos.router)
app.include_router(insumos.router)
app.include_router(clientes.router)
app.include_router(vendas.router)
app.include_router(caixa.router)
app.include_router(lojas.router)
app.include_router(cardapio.router)
app.include_router(admin.router)
