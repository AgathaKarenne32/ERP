from pydantic import BaseModel

from app.schemas.order import OrderOut


class SellerDashboard(BaseModel):
    store_name: str
    reputation_score: float
    active_products: int
    total_orders: int
    revenue_cents: int


class SellerOrdersOut(BaseModel):
    items: list[OrderOut]
