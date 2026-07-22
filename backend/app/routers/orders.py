import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.db import get_session
from app.core.deps import get_current_user
from app.models.order import Order
from app.models.user import User
from app.routers.serializers import order_out
from app.schemas.order import OrderOut
from app.services.checkout import checkout

router = APIRouter(tags=["orders"])


@router.post("/checkout", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create_checkout(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> OrderOut:
    order = checkout(session, user.id)
    return order_out(session, order)


@router.get("/orders", response_model=list[OrderOut])
def list_orders(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[OrderOut]:
    orders = session.exec(
        select(Order).where(Order.buyer_id == user.id).order_by(Order.created_at.desc())
    ).all()
    return [order_out(session, o) for o in orders]


@router.get("/orders/{order_id}", response_model=OrderOut)
def get_order(
    order_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> OrderOut:
    order = session.get(Order, order_id)
    if order is None or order.buyer_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    return order_out(session, order)
