import uuid

from sqlmodel import Field, SQLModel

from app.models.base import pk_field


class CartItem(SQLModel, table=True):
    __tablename__ = "cart_items"

    id: uuid.UUID = pk_field()
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    product_id: uuid.UUID = Field(foreign_key="products.id", index=True)
    quantity: int = Field(default=1)
