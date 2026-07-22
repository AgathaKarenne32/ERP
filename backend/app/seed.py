"""Demo data seeding.

Populates two sellers with stores, ~10 products across 3 categories, one buyer,
one already-DELIVERED order (so reviews can be demoed immediately) and a couple
of sample chat messages. Runs once on first startup (it is a no-op if a user
already exists). Demo credentials are documented in the README.
"""

import logging

from sqlmodel import Session, select

from app.core.db import engine
from app.core.security import hash_password
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
from app.models.shipment import Shipment
from app.models.user import SellerProfile, User
from app.services.shipping import default_estimated_delivery, generate_tracking_code

logger = logging.getLogger("seed")

DEMO_PASSWORD = "demo1234"


def _seller(session: Session, name: str, email: str, store: str) -> SellerProfile:
    user = User(
        name=name,
        email=email,
        password_hash=hash_password(DEMO_PASSWORD),
        role=UserRole.SELLER,
    )
    session.add(user)
    session.flush()
    profile = SellerProfile(user_id=user.id, store_name=store)
    session.add(profile)
    session.flush()
    return profile


def seed() -> None:
    with Session(engine) as session:
        # Idempotent: skip if the DB already has users.
        if session.exec(select(User)).first() is not None:
            logger.info("Seed skipped: data already present")
            return

        logger.info("Seeding demo data...")

        techstore = _seller(session, "Alice Tech", "seller1@demo.com", "TechStore")
        casa = _seller(session, "Bruno Casa", "seller2@demo.com", "Casa & Conforto")

        # ~10 products across 3 categories.
        products_data = [
            (
                techstore,
                "Fone Bluetooth XZ",
                "Fone sem fio com cancelamento de ruído",
                19900,
                50,
                "eletronicos",
            ),
            (
                techstore,
                "Teclado Mecânico RGB",
                "Switch azul, retroiluminado",
                29900,
                30,
                "eletronicos",
            ),
            (
                techstore,
                "Mouse Gamer 12000dpi",
                "Sensor óptico de alta precisão",
                14900,
                40,
                "eletronicos",
            ),
            (
                techstore,
                "Webcam Full HD",
                "1080p com microfone integrado",
                17900,
                25,
                "eletronicos",
            ),
            (
                techstore,
                "Smartwatch Fit",
                "Monitor de batimentos e passos",
                39900,
                20,
                "eletronicos",
            ),
            (casa, "Jogo de Panelas 5pç", "Antiaderente, base tripla", 34900, 15, "casa"),
            (casa, "Luminária de Mesa LED", "Três temperaturas de cor", 8900, 60, "casa"),
            (casa, "Cafeteira Compacta", "Preparo rápido para 6 xícaras", 22900, 18, "casa"),
            (casa, "Camiseta Básica Algodão", "Malha 100% algodão, unissex", 4900, 100, "moda"),
            (casa, "Tênis Casual Urbano", "Confortável para o dia a dia", 25900, 35, "moda"),
        ]
        products: list[Product] = []
        for seller, title, desc, price, stock, cat in products_data:
            p = Product(
                seller_id=seller.id,
                title=title,
                description=desc,
                price_cents=price,
                stock=stock,
                category=cat,
                images=[f"https://picsum.photos/seed/{title[:6].strip()}/600/400"],
                status=ProductStatus.ACTIVE,
            )
            session.add(p)
            products.append(p)
        session.flush()

        # Buyer.
        buyer = User(
            name="Carla Compradora",
            email="buyer@demo.com",
            password_hash=hash_password(DEMO_PASSWORD),
            role=UserRole.BUYER,
        )
        session.add(buyer)
        session.flush()

        # One already-DELIVERED order so a review can be posted in the demo.
        first = products[0]
        order = Order(
            buyer_id=buyer.id,
            total_cents=first.price_cents * 1,
            status=OrderStatus.DELIVERED,
            payment_status=PaymentStatus.PAID,
        )
        session.add(order)
        session.flush()
        session.add(
            OrderItem(
                order_id=order.id,
                product_id=first.id,
                title_snapshot=first.title,
                unit_price_cents=first.price_cents,
                quantity=1,
            )
        )
        session.add(
            Shipment(
                order_id=order.id,
                status=ShipmentStatus.DELIVERED,
                tracking_code=generate_tracking_code(),
                estimated_delivery=default_estimated_delivery(),
            )
        )
        # count the delivered sale on the seller
        techstore.sales_count += 1
        session.add(techstore)

        # Sample chat messages tied to the delivered order.
        session.add(
            ChatMessage(
                user_id=buyer.id,
                order_id=order.id,
                role=ChatRole.USER,
                content="Olá, meu pedido já foi entregue?",
            )
        )
        session.add(
            ChatMessage(
                user_id=buyer.id,
                order_id=order.id,
                role=ChatRole.ASSISTANT,
                content="Sim! Seu pedido consta como ENTREGUE. Posso ajudar com mais algo?",
            )
        )

        session.commit()
        logger.info("Seed complete.")
