import uuid

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models.cart import CartItem
from app.models.enums import OrderStatus, PaymentStatus, ShipmentStatus
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.shipment import Shipment
from app.models.user import SellerProfile
from app.services.payment import payment_service
from app.services.shipping import default_estimated_delivery, generate_tracking_code


def checkout(session: Session, buyer_id: uuid.UUID) -> Order:
    """Turn the buyer's cart into a paid order.

    Steps (kept in one transaction so a failure leaves no half-order):
    validate cart & stock -> create Order + OrderItems (price snapshot) ->
    charge payment (mock) -> decrement stock, bump seller sales_count ->
    create Shipment (PREPARING) -> clear cart.
    """
    cart_items = session.exec(select(CartItem).where(CartItem.user_id == buyer_id)).all()
    if not cart_items:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cart is empty")

    # Load products and validate availability up front.
    lines: list[tuple[CartItem, Product]] = []
    total_cents = 0
    for item in cart_items:
        product = session.get(Product, item.product_id)
        if product is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Product no longer exists")
        if product.stock < item.quantity:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Insufficient stock for '{product.title}'",
            )
        total_cents += product.price_cents * item.quantity
        lines.append((item, product))

    order = Order(
        buyer_id=buyer_id,
        total_cents=total_cents,
        status=OrderStatus.PENDING,
        payment_status=PaymentStatus.UNPAID,
    )
    session.add(order)
    session.flush()  # assign order.id before creating children

    currency = lines[0][1].currency
    for item, product in lines:
        session.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                title_snapshot=product.title,
                unit_price_cents=product.price_cents,
                quantity=item.quantity,
            )
        )

    # Charge via the (mock) payment gateway. A real gateway failure would
    # roll back the whole transaction below.
    result = payment_service.charge(amount_cents=total_cents, currency=currency, buyer_id=buyer_id)
    if not result.success:
        session.rollback()
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, "Payment declined")

    order.payment_status = PaymentStatus.PAID
    order.status = OrderStatus.PAID

    # Decrement stock and credit each seller's sales counter.
    for item, product in lines:
        product.stock -= item.quantity
        session.add(product)
        seller = session.get(SellerProfile, product.seller_id)
        if seller is not None:
            seller.sales_count += item.quantity
            session.add(seller)

    # Paying immediately kicks off fulfillment: a shipment starts PREPARING.
    shipment = Shipment(
        order_id=order.id,
        status=ShipmentStatus.PREPARING,
        tracking_code=generate_tracking_code(),
        estimated_delivery=default_estimated_delivery(),
    )
    session.add(shipment)

    # Clear the cart now that it became an order.
    for item, _ in lines:
        session.delete(item)

    session.commit()
    session.refresh(order)
    return order
