import uuid
from datetime import datetime

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.models.base import created_field, pk_field
from app.models.enums import ProductStatus


class Product(SQLModel, table=True):
    __tablename__ = "products"

    id: uuid.UUID = pk_field()
    seller_id: uuid.UUID = Field(foreign_key="seller_profiles.id", index=True)
    title: str = Field(index=True)
    description: str = ""
    # Prices are always stored in integer cents to avoid floating-point rounding.
    price_cents: int
    currency: str = Field(default="BRL")
    stock: int = Field(default=0)
    category: str = Field(index=True)
    # Image storage is out of scope for the MVP: we accept a list of URLs.
    images: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    status: ProductStatus = Field(default=ProductStatus.ACTIVE)
    created_at: datetime = created_field()
