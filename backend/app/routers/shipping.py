import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.db import get_session
from app.core.deps import require_seller
from app.models.base import utcnow
from app.models.enums import OrderStatus, ShipmentStatus
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.shipment import Shipment
from app.models.user import SellerProfile
from app.routers.serializers import shipment_out
from app.schemas.order import ShipmentOut, TrackingEvent, TrackingOut
from app.services.shipping import SHIPMENT_FLOW, next_status, status_label

router = APIRouter(tags=["shipping"])


def _seller_owns_order(session: Session, order_id: uuid.UUID, seller_id: uuid.UUID) -> bool:
    """A seller may advance a shipment only if the order contains one of their
    products."""
    item_products = session.exec(
        select(OrderItem.product_id).where(OrderItem.order_id == order_id)
    ).all()
    for pid in item_products:
        product = session.get(Product, pid)
        if product and product.seller_id == seller_id:
            return True
    return False


@router.patch("/shipments/{shipment_id}/advance", response_model=ShipmentOut)
def advance_shipment(
    shipment_id: uuid.UUID,
    seller: SellerProfile = Depends(require_seller),
    session: Session = Depends(get_session),
) -> ShipmentOut:
    shipment = session.get(Shipment, shipment_id)
    if shipment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Shipment not found")
    if not _seller_owns_order(session, shipment.order_id, seller.id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your order")

    nxt = next_status(shipment.status)
    if nxt is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Shipment already delivered")

    shipment.status = nxt
    shipment.updated_at = utcnow()
    session.add(shipment)

    # Keep the parent order's lifecycle in sync with fulfillment.
    order = session.get(Order, shipment.order_id)
    if order:
        if nxt == ShipmentStatus.IN_TRANSIT:
            order.status = OrderStatus.SHIPPED
        elif nxt == ShipmentStatus.DELIVERED:
            order.status = OrderStatus.DELIVERED  # delivery unlocks reviews
        session.add(order)

    session.commit()
    session.refresh(shipment)
    return shipment_out(shipment)


@router.get("/shipments/track/{code}", response_model=TrackingOut)
def track(code: str, session: Session = Depends(get_session)) -> TrackingOut:
    # Public tracking: no auth required, just the code.
    shipment = session.exec(select(Shipment).where(Shipment.tracking_code == code)).first()
    if shipment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tracking code not found")

    current_idx = SHIPMENT_FLOW.index(shipment.status)
    timeline = [
        TrackingEvent(status=s, label=status_label(s), reached=i <= current_idx)
        for i, s in enumerate(SHIPMENT_FLOW)
    ]
    return TrackingOut(
        tracking_code=shipment.tracking_code,
        current_status=shipment.status,
        estimated_delivery=shipment.estimated_delivery,
        timeline=timeline,
    )
