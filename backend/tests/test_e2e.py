"""End-to-end integration test covering the full marketplace flow:
register seller -> create product -> register buyer -> add to cart -> checkout
-> advance shipment to delivered -> review -> reputation updated -> chat.
"""


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_full_purchase_flow(client):
    # --- Seller registers and logs in ---
    r = client.post(
        "/api/auth/register",
        json={
            "name": "Sam Seller",
            "email": "sam@shop.com",
            "password": "secret123",
            "role": "SELLER",
            "store_name": "Sam's Shop",
        },
    )
    assert r.status_code == 201, r.text

    r = client.post("/api/auth/login", json={"email": "sam@shop.com", "password": "secret123"})
    assert r.status_code == 200
    seller_token = r.json()["access_token"]

    # --- Seller creates a product ---
    r = client.post(
        "/api/products",
        headers=_auth(seller_token),
        json={
            "title": "Cool Gadget",
            "description": "A very cool gadget",
            "price_cents": 5000,
            "stock": 10,
            "category": "eletronicos",
            "images": ["https://example.com/g.png"],
        },
    )
    assert r.status_code == 201, r.text
    product = r.json()
    product_id = product["id"]
    assert product["seller"]["store_name"] == "Sam's Shop"

    # --- Public search finds it ---
    r = client.get("/api/products", params={"q": "gadget"})
    assert r.status_code == 200
    assert r.json()["total"] == 1

    # --- Buyer registers and logs in ---
    client.post(
        "/api/auth/register",
        json={
            "name": "Bea Buyer",
            "email": "bea@buy.com",
            "password": "secret123",
            "role": "BUYER",
        },
    )
    r = client.post("/api/auth/login", json={"email": "bea@buy.com", "password": "secret123"})
    buyer_token = r.json()["access_token"]

    # --- Add to cart ---
    r = client.post(
        "/api/cart/items",
        headers=_auth(buyer_token),
        json={"product_id": product_id, "quantity": 2},
    )
    assert r.status_code == 201, r.text
    cart = r.json()
    assert cart["total_cents"] == 10000

    # --- Checkout ---
    r = client.post("/api/checkout", headers=_auth(buyer_token))
    assert r.status_code == 201, r.text
    order = r.json()
    order_id = order["id"]
    assert order["status"] == "PAID"
    assert order["payment_status"] == "PAID"
    assert order["shipment"]["status"] == "PREPARING"
    tracking_code = order["shipment"]["tracking_code"]
    shipment_id = order["shipment"]["id"]

    # Stock was decremented.
    r = client.get(f"/api/products/{product_id}")
    assert r.json()["stock"] == 8

    # --- Public tracking works ---
    r = client.get(f"/api/shipments/track/{tracking_code}")
    assert r.status_code == 200
    assert r.json()["current_status"] == "PREPARING"

    # --- Seller advances shipment: PREPARING -> IN_TRANSIT -> DELIVERED ---
    r = client.patch(f"/api/shipments/{shipment_id}/advance", headers=_auth(seller_token))
    assert r.json()["status"] == "IN_TRANSIT"
    r = client.patch(f"/api/shipments/{shipment_id}/advance", headers=_auth(seller_token))
    assert r.json()["status"] == "DELIVERED"

    # Order is now DELIVERED.
    r = client.get(f"/api/orders/{order_id}", headers=_auth(buyer_token))
    assert r.json()["status"] == "DELIVERED"

    # --- Buyer reviews the delivered product ---
    r = client.post(
        f"/api/products/{product_id}/reviews",
        headers=_auth(buyer_token),
        json={"rating": 4, "comment": "Works great!"},
    )
    assert r.status_code == 201, r.text

    # Reputation recalculated to the review's rating.
    r = client.get(f"/api/products/{product_id}")
    assert r.json()["seller"]["reputation_score"] == 4.0

    # --- Seller dashboard reflects the sale ---
    r = client.get("/api/seller/dashboard", headers=_auth(seller_token))
    dash = r.json()
    assert dash["total_orders"] == 1
    assert dash["revenue_cents"] == 10000

    # --- AI chat responds (offline demo mode, no API key) ---
    r = client.post(
        "/api/chat",
        headers=_auth(buyer_token),
        json={"message": "Where is my order?", "order_id": order_id},
    )
    assert r.status_code == 200
    assert r.json()["reply"]["role"] == "ASSISTANT"


def test_review_forbidden_without_delivery(client):
    client.post(
        "/api/auth/register",
        json={"name": "B", "email": "b@b.com", "password": "secret123", "role": "BUYER"},
    )
    token = client.post(
        "/api/auth/login", json={"email": "b@b.com", "password": "secret123"}
    ).json()["access_token"]

    client.post(
        "/api/auth/register",
        json={
            "name": "S",
            "email": "s@s.com",
            "password": "secret123",
            "role": "SELLER",
            "store_name": "S",
        },
    )
    stoken = client.post(
        "/api/auth/login", json={"email": "s@s.com", "password": "secret123"}
    ).json()["access_token"]
    pid = client.post(
        "/api/products",
        headers=_auth(stoken),
        json={"title": "X", "price_cents": 100, "stock": 5, "category": "c"},
    ).json()["id"]

    # No delivered order -> review must be rejected.
    r = client.post(
        f"/api/products/{pid}/reviews",
        headers=_auth(token),
        json={"rating": 5, "comment": "nope"},
    )
    assert r.status_code == 403
