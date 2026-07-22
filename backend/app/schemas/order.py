import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import OrderStatus, PaymentStatus, ShipmentStatus


class OrderItemOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    title_snapshot: str
    unit_price_cents: int
    quantity: int


class ShipmentOut(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    status: ShipmentStatus
    tracking_code: str
    estimated_delivery: datetime | None
    updated_at: datetime


class OrderOut(BaseModel):
    id: uuid.UUID
    buyer_id: uuid.UUID
    total_cents: int
    status: OrderStatus
    payment_status: PaymentStatus
    created_at: datetime
    items: list[OrderItemOut]
    shipment: ShipmentOut | None = None


class TrackingEvent(BaseModel):
    status: ShipmentStatus
    label: str
    reached: bool


class TrackingOut(BaseModel):
    tracking_code: str
    current_status: ShipmentStatus
    estimated_delivery: datetime | None
    timeline: list[TrackingEvent]
