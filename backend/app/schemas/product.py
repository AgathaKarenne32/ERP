import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import ProductStatus


class ProductCreate(BaseModel):
    title: str
    description: str = ""
    price_cents: int = Field(gt=0)
    currency: str = "BRL"
    stock: int = Field(ge=0)
    category: str
    images: list[str] = []


class ProductUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    price_cents: int | None = Field(default=None, gt=0)
    stock: int | None = Field(default=None, ge=0)
    category: str | None = None
    images: list[str] | None = None
    status: ProductStatus | None = None


class SellerInfo(BaseModel):
    id: uuid.UUID
    store_name: str
    reputation_score: float
    sales_count: int


class ProductOut(BaseModel):
    id: uuid.UUID
    seller_id: uuid.UUID
    title: str
    description: str
    price_cents: int
    currency: str
    stock: int
    category: str
    images: list[str]
    status: ProductStatus
    created_at: datetime
    seller: SellerInfo | None = None


class ProductListOut(BaseModel):
    items: list[ProductOut]
    total: int
    limit: int
    offset: int
