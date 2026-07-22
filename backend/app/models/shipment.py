import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from app.models.base import pk_field, utcnow
from app.models.enums import ShipmentStatus


class Shipment(SQLModel, table=True):
    __tablename__ = "shipments"

    id: uuid.UUID = pk_field()
    order_id: uuid.UUID = Field(foreign_key="orders.id", index=True, unique=True)
    status: ShipmentStatus = Field(default=ShipmentStatus.PREPARING)
    tracking_code: str = Field(index=True, unique=True)
    estimated_delivery: datetime | None = None
    updated_at: datetime = Field(default_factory=utcnow)
