import uuid

from pydantic import BaseModel, Field

from app.schemas.product import ProductOut


class CartItemCreate(BaseModel):
    product_id: uuid.UUID
    quantity: int = Field(default=1, gt=0)


class CartItemUpdate(BaseModel):
    quantity: int = Field(gt=0)


class CartItemOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    quantity: int
    product: ProductOut
    line_total_cents: int


class CartOut(BaseModel):
    items: list[CartItemOut]
    total_cents: int
