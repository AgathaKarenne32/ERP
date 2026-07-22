from enum import Enum


class UserRole(str, Enum):
    BUYER = "BUYER"
    SELLER = "SELLER"
    ADMIN = "ADMIN"


class ProductStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class PaymentStatus(str, Enum):
    UNPAID = "UNPAID"
    PAID = "PAID"
    REFUNDED = "REFUNDED"


class ShipmentStatus(str, Enum):
    PREPARING = "PREPARING"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"


class ChatRole(str, Enum):
    USER = "USER"
    ASSISTANT = "ASSISTANT"
