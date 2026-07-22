"""Aggregate model imports so `import app.models` registers every table on
SQLModel.metadata (used by create_all and Alembic autogenerate)."""

from app.models.cart import CartItem
from app.models.chat import ChatMessage
from app.models.enums import (
    ChatRole,
    OrderStatus,
    PaymentStatus,
    ProductStatus,
    ShipmentStatus,
    UserRole,
)
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.review import Review
from app.models.shipment import Shipment
from app.models.user import SellerProfile, User

__all__ = [
    "CartItem",
    "ChatMessage",
    "ChatRole",
    "Order",
    "OrderItem",
    "OrderStatus",
    "PaymentStatus",
    "Product",
    "ProductStatus",
    "Review",
    "Shipment",
    "ShipmentStatus",
    "SellerProfile",
    "User",
    "UserRole",
]
