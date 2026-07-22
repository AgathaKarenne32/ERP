"""Shared serialization helpers to build response schemas from ORM rows."""

from sqlmodel import Session

from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.shipment import Shipment
from app.models.user import SellerProfile
from app.schemas.order import OrderItemOut, OrderOut, ShipmentOut
from app.schemas.product import ProductOut, SellerInfo


def product_out(session: Session, product: Product) -> ProductOut:
    seller = session.get(SellerProfile, product.seller_id)
    seller_info = (
        SellerInfo(
            id=seller.id,
            store_name=seller.store_name,
            reputation_score=seller.reputation_score,
            sales_count=seller.sales_count,
        )
        if seller
        else None
    )
    return ProductOut(
        **product.model_dump(),
        seller=seller_info,
    )


def shipment_out(shipment: Shipment) -> ShipmentOut:
    return ShipmentOut(**shipment.model_dump())


def order_out(session: Session, order: Order) -> OrderOut:
    from sqlmodel import select

    items = session.exec(select(OrderItem).where(OrderItem.order_id == order.id)).all()
    shipment = session.exec(select(Shipment).where(Shipment.order_id == order.id)).first()
    return OrderOut(
        **order.model_dump(),
        items=[OrderItemOut(**i.model_dump()) for i in items],
        shipment=shipment_out(shipment) if shipment else None,
    )
