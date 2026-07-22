import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, func, select

from app.core.db import get_session
from app.core.deps import get_current_user
from app.models.enums import OrderStatus
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.review import Review
from app.models.user import SellerProfile, User
from app.schemas.review import ReviewCreate, ReviewOut

router = APIRouter(prefix="/products", tags=["reviews"])


def _recalculate_reputation(session: Session, seller_id: uuid.UUID) -> None:
    """Seller reputation = average rating across all reviews of their products.
    Defaults back to 5.0 when there are no reviews yet."""
    product_ids = session.exec(select(Product.id).where(Product.seller_id == seller_id)).all()
    if not product_ids:
        return
    avg = session.exec(
        select(func.avg(Review.rating)).where(Review.product_id.in_(product_ids))
    ).one()
    seller = session.get(SellerProfile, seller_id)
    if seller:
        seller.reputation_score = round(float(avg), 2) if avg is not None else 5.0
        session.add(seller)


@router.post("/{product_id}/reviews", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
def create_review(
    product_id: uuid.UUID,
    payload: ReviewCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ReviewOut:
    product = session.get(Product, product_id)
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")

    # Only a buyer who has a DELIVERED order containing this product may review it.
    delivered_order = session.exec(
        select(Order)
        .join(OrderItem, OrderItem.order_id == Order.id)
        .where(
            Order.buyer_id == user.id,
            Order.status == OrderStatus.DELIVERED,
            OrderItem.product_id == product_id,
        )
    ).first()
    if delivered_order is None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "You can only review products from a delivered order",
        )

    # One review per (buyer, product, order).
    already = session.exec(
        select(Review).where(
            Review.buyer_id == user.id,
            Review.product_id == product_id,
            Review.order_id == delivered_order.id,
        )
    ).first()
    if already:
        raise HTTPException(status.HTTP_409_CONFLICT, "You already reviewed this product")

    review = Review(
        product_id=product_id,
        buyer_id=user.id,
        order_id=delivered_order.id,
        rating=payload.rating,
        comment=payload.comment,
    )
    session.add(review)
    session.flush()
    _recalculate_reputation(session, product.seller_id)
    session.commit()
    session.refresh(review)
    return ReviewOut(**review.model_dump())


@router.get("/{product_id}/reviews", response_model=list[ReviewOut])
def list_reviews(product_id: uuid.UUID, session: Session = Depends(get_session)) -> list[ReviewOut]:
    reviews = session.exec(
        select(Review).where(Review.product_id == product_id).order_by(Review.created_at.desc())
    ).all()
    return [ReviewOut(**r.model_dump()) for r in reviews]
