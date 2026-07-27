from contextlib import asynccontextmanager

from fastapi import FastAPI

from .core.db import init_db
from .routers import auth, caixa, clientes, insumos, produtos, vendas
from .seed import seed_demo_data


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    seed_demo_data()
    yield


app = FastAPI(title="Eclética API", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "ecletica-api"}


app.include_router(auth.router)
app.include_router(produtos.router)
app.include_router(insumos.router)
app.include_router(clientes.router)
app.include_router(vendas.router)
app.include_router(caixa.router)
