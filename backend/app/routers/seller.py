from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.core.db import get_session
from app.core.deps import require_seller
from app.models.enums import OrderStatus, ProductStatus
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.user import SellerProfile
from app.routers.serializers import order_out, product_out
from app.schemas.product import ProductOut
from app.schemas.seller import SellerDashboard

router = APIRouter(prefix="/seller", tags=["seller"])


@router.get("/products", response_model=list[ProductOut])
def my_products(
    seller: SellerProfile = Depends(require_seller),
    session: Session = Depends(get_session),
) -> list[ProductOut]:
    products = session.exec(
        select(Product).where(Product.seller_id == seller.id).order_by(Product.created_at.desc())
    ).all()
    return [product_out(session, p) for p in products]


def _seller_order_ids(session: Session, seller_id) -> list:
    """Order ids that contain at least one of the seller's products."""
    product_ids = session.exec(select(Product.id).where(Product.seller_id == seller_id)).all()
    if not product_ids:
        return []
    order_ids = session.exec(
        select(OrderItem.order_id).where(OrderItem.product_id.in_(product_ids)).distinct()
    ).all()
    return list(order_ids)


@router.get("/orders")
def received_orders(
    seller: SellerProfile = Depends(require_seller),
    session: Session = Depends(get_session),
):
    order_ids = _seller_order_ids(session, seller.id)
    if not order_ids:
        return {"items": []}
    orders = session.exec(
        select(Order).where(Order.id.in_(order_ids)).order_by(Order.created_at.desc())
    ).all()
    return {"items": [order_out(session, o) for o in orders]}


@router.get("/dashboard", response_model=SellerDashboard)
def dashboard(
    seller: SellerProfile = Depends(require_seller),
    session: Session = Depends(get_session),
) -> SellerDashboard:
    active_products = len(
        session.exec(
            select(Product.id).where(
                Product.seller_id == seller.id,
                Product.status == ProductStatus.ACTIVE,
            )
        ).all()
    )

    order_ids = _seller_order_ids(session, seller.id)
    orders = session.exec(select(Order).where(Order.id.in_(order_ids))).all() if order_ids else []
    # Revenue counts only paid/fulfilled orders (exclude pending/cancelled).
    revenue = sum(
        o.total_cents
        for o in orders
        if o.status in (OrderStatus.PAID, OrderStatus.SHIPPED, OrderStatus.DELIVERED)
    )

    return SellerDashboard(
        store_name=seller.store_name,
        reputation_score=seller.reputation_score,
        active_products=active_products,
        total_orders=len(orders),
        revenue_cents=revenue,
    )
