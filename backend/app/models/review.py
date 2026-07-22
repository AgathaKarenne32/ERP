import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from app.models.base import created_field, pk_field


class Review(SQLModel, table=True):
    __tablename__ = "reviews"

    id: uuid.UUID = pk_field()
    product_id: uuid.UUID = Field(foreign_key="products.id", index=True)
    buyer_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    order_id: uuid.UUID = Field(foreign_key="orders.id", index=True)
    rating: int  # 1..5, validated at the schema layer
    comment: str = ""
    created_at: datetime = created_field()
