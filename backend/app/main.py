import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.db import create_db_and_tables
from app.routers import (
    auth,
    cart,
    chat,
    health,
    orders,
    products,
    reviews,
    seller,
    shipping,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # On first boot: create the schema (idempotent) and seed demo data so the
    # whole flow is demonstrable right after `docker compose up`.
    create_db_and_tables()
    if settings.run_seed:
        from app.seed import seed

        seed()
    logger.info("Startup complete.")
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Standardize errors as JSON { "detail": ... } across the whole API.
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


# All API routes live under /api.
prefix = settings.api_prefix
app.include_router(health.router, prefix=prefix)
app.include_router(auth.router, prefix=prefix)
app.include_router(auth.me_router, prefix=prefix)
app.include_router(products.router, prefix=prefix)
app.include_router(reviews.router, prefix=prefix)  # /products/{id}/reviews
app.include_router(cart.router, prefix=prefix)
app.include_router(orders.router, prefix=prefix)
app.include_router(shipping.router, prefix=prefix)
app.include_router(seller.router, prefix=prefix)
app.include_router(chat.router, prefix=prefix)
