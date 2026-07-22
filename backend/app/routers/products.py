import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, func, select

from app.core.db import get_session
from app.core.deps import require_seller
from app.models.enums import ProductStatus
from app.models.product import Product
from app.models.user import SellerProfile
from app.routers.serializers import product_out
from app.schemas.product import (
    ProductCreate,
    ProductListOut,
    ProductOut,
    ProductUpdate,
)

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=ProductListOut)
def list_products(
    session: Session = Depends(get_session),
    q: str | None = Query(default=None, description="Free-text search on title/description"),
    category: str | None = None,
    min_price_cents: int | None = Query(default=None, ge=0),
    max_price_cents: int | None = Query(default=None, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ProductListOut:
    # Public storefront listing: only ACTIVE products are visible.
    conditions = [Product.status == ProductStatus.ACTIVE]
    if q:
        like = f"%{q}%"
        # ILIKE gives case-insensitive substring match on Postgres; on SQLite
        # LIKE is already case-insensitive for ASCII, so tests behave the same.
        conditions.append(Product.title.ilike(like) | Product.description.ilike(like))
    if category:
        conditions.append(Product.category == category)
    if min_price_cents is not None:
        conditions.append(Product.price_cents >= min_price_cents)
    if max_price_cents is not None:
        conditions.append(Product.price_cents <= max_price_cents)

    total = session.exec(select(func.count()).select_from(Product).where(*conditions)).one()
    rows = session.exec(
        select(Product)
        .where(*conditions)
        .order_by(Product.created_at.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return ProductListOut(
        items=[product_out(session, p) for p in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: uuid.UUID, session: Session = Depends(get_session)) -> ProductOut:
    product = session.get(Product, product_id)
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    return product_out(session, product)


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate,
    seller: SellerProfile = Depends(require_seller),
    session: Session = Depends(get_session),
) -> ProductOut:
    product = Product(seller_id=seller.id, **payload.model_dump())
    session.add(product)
    session.commit()
    session.refresh(product)
    return product_out(session, product)


@router.patch("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: uuid.UUID,
    payload: ProductUpdate,
    seller: SellerProfile = Depends(require_seller),
    session: Session = Depends(get_session),
) -> ProductOut:
    product = session.get(Product, product_id)
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    if product.seller_id != seller.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your product")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    session.add(product)
    session.commit()
    session.refresh(product)
    return product_out(session, product)
