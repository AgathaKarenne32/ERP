import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.db import get_session
from app.core.deps import get_current_user
from app.models.cart import CartItem
from app.models.product import Product
from app.models.user import User
from app.routers.serializers import product_out
from app.schemas.cart import CartItemCreate, CartItemOut, CartItemUpdate, CartOut

router = APIRouter(prefix="/cart", tags=["cart"])


def _cart_out(session: Session, user_id: uuid.UUID) -> CartOut:
    items = session.exec(select(CartItem).where(CartItem.user_id == user_id)).all()
    out_items: list[CartItemOut] = []
    total = 0
    for item in items:
        product = session.get(Product, item.product_id)
        if product is None:
            continue
        line = product.price_cents * item.quantity
        total += line
        out_items.append(
            CartItemOut(
                id=item.id,
                product_id=item.product_id,
                quantity=item.quantity,
                product=product_out(session, product),
                line_total_cents=line,
            )
        )
    return CartOut(items=out_items, total_cents=total)


@router.get("", response_model=CartOut)
def get_cart(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> CartOut:
    return _cart_out(session, user.id)


@router.post("/items", response_model=CartOut, status_code=status.HTTP_201_CREATED)
def add_item(
    payload: CartItemCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> CartOut:
    product = session.get(Product, payload.product_id)
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")

    # If the product is already in the cart, bump quantity instead of duplicating.
    existing = session.exec(
        select(CartItem).where(
            CartItem.user_id == user.id, CartItem.product_id == payload.product_id
        )
    ).first()
    if existing:
        existing.quantity += payload.quantity
        session.add(existing)
    else:
        session.add(
            CartItem(user_id=user.id, product_id=payload.product_id, quantity=payload.quantity)
        )
    session.commit()
    return _cart_out(session, user.id)


@router.patch("/items/{item_id}", response_model=CartOut)
def update_item(
    item_id: uuid.UUID,
    payload: CartItemUpdate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> CartOut:
    item = session.get(CartItem, item_id)
    if item is None or item.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cart item not found")
    item.quantity = payload.quantity
    session.add(item)
    session.commit()
    return _cart_out(session, user.id)


@router.delete("/items/{item_id}", response_model=CartOut)
def remove_item(
    item_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> CartOut:
    item = session.get(CartItem, item_id)
    if item is None or item.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cart item not found")
    session.delete(item)
    session.commit()
    return _cart_out(session, user.id)
