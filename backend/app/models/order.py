import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from app.models.base import created_field, pk_field
from app.models.enums import OrderStatus, PaymentStatus


class Order(SQLModel, table=True):
    __tablename__ = "orders"

    id: uuid.UUID = pk_field()
    buyer_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    total_cents: int
    status: OrderStatus = Field(default=OrderStatus.PENDING)
    payment_status: PaymentStatus = Field(default=PaymentStatus.UNPAID)
    created_at: datetime = created_field()


class OrderItem(SQLModel, table=True):
    __tablename__ = "order_items"

    id: uuid.UUID = pk_field()
    order_id: uuid.UUID = Field(foreign_key="orders.id", index=True)
    product_id: uuid.UUID = Field(foreign_key="products.id", index=True)
    # Snapshot title/price at purchase time so later catalog edits never
    # retroactively change what the buyer actually paid for.
    title_snapshot: str
    unit_price_cents: int
    quantity: int
