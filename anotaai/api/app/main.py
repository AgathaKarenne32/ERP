from contextlib import asynccontextmanager

from fastapi import FastAPI

from .core.db import init_db
from .routers import auth, comandas, kds, relatorios
from .seed import seed_demo_data


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    seed_demo_data()
    yield


app = FastAPI(title="AnotaAi-like API", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "anotaai-api"}


app.include_router(auth.router)
app.include_router(comandas.router)
app.include_router(kds.router)
app.include_router(relatorios.router)
