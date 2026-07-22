# Architecture

## Services

```
┌─────────────────┐        ┌──────────────────────┐        ┌────────────────┐
│  Angular 18 SPA │  HTTP  │   FastAPI backend    │  SQL   │  PostgreSQL 16 │
│  (browser)      │ ─────► │   (uvicorn)          │ ─────► │                │
│                 │  /api  │                      │        │                │
│  - signals      │        │  - JWT auth          │        └────────────────┘
│  - typed client │        │  - business services │
│    (from OpenAPI)│       │  - OpenAPI /docs     │        ┌────────────────┐
│  - chat widget  │        │  - ai_chat service ──┼──────► │  Anthropic API │
└─────────────────┘        └──────────────────────┘  HTTPS │ claude-sonnet  │
                                                            └────────────────┘
```

- **Frontend** and **backend** are fully decoupled: the browser talks only to
  the REST API under `/api`. The Angular API client is **generated** from the
  backend's OpenAPI schema, so there is a single source of truth for the
  contract and no hand-written DTOs.
- The **AI key never reaches the browser** — only the backend calls Anthropic.
- In dev, the Angular dev server (`:4200`) hits the backend (`:8000`) directly
  with CORS enabled. In prod, Nginx serves the static bundle and proxies `/api`
  to the backend (same origin, no CORS).

## Data model

PKs are UUIDs; `created_at`/`updated_at` on rows that need them. **Prices are
integer cents** everywhere to avoid floating-point errors. Status fields are
Python enums.

```
User ──1:1──> SellerProfile
 │  (role: BUYER | SELLER | ADMIN)      (store_name, reputation_score, sales_count)
 │
 └──< CartItem >── Product ──< OrderItem >── Order
                     │  (seller_id, price_cents,        │ (buyer_id, total_cents,
                     │   stock, category, images,       │  status, payment_status)
                     │   status)                        │
                     │                                  ├──1:1── Shipment
                     └──< Review >──────────────────────┘        (status, tracking_code,
                          (rating, comment, order_id)             estimated_delivery)

ChatMessage (user_id, order_id?, role: USER|ASSISTANT, content)
```

| Table            | Purpose                                                        |
| ---------------- | -------------------------------------------------------------- |
| `users`          | Accounts; `role` drives the primary view. Anyone can buy.      |
| `seller_profiles`| Storefront + reputation (avg of the seller's product reviews). |
| `products`       | Catalog items. `images` is a JSON list of URLs.                |
| `cart_items`     | Server-side cart, one row per (user, product).                 |
| `orders`         | Purchase header (`status`, `payment_status`).                  |
| `order_items`    | Line items with **price/title snapshot** at purchase time.     |
| `shipments`      | One per order; linear status flow + tracking code.             |
| `reviews`        | 1–5 rating; only allowed for a delivered order's products.     |
| `chat_messages`  | Persisted AI conversation, optionally tied to an order.        |

## End-to-end flow of an order

1. **Seller** registers (role `SELLER` → a `SellerProfile` is created) and lists
   a `Product`.
2. **Buyer** searches the public catalog (`ILIKE` + category/price filters +
   limit/offset paging), opens the product, and adds it to the server-side cart.
3. **Checkout** (`POST /api/checkout`, one DB transaction):
   - validates cart + stock,
   - creates `Order` + `OrderItem`s (snapshotting price/title),
   - calls the **mock `PaymentService`** (approves after ~1s),
   - on approval: `payment_status=PAID`, `status=PAID`, decrements stock, bumps
     each seller's `sales_count`,
   - creates a `Shipment` in `PREPARING` with a generated `tracking_code`,
   - clears the cart.
4. **Fulfillment**: the seller advances the shipment
   `PREPARING → IN_TRANSIT → DELIVERED` (`PATCH /api/shipments/{id}/advance`).
   The parent order tracks along (`SHIPPED`, then `DELIVERED`).
   Public tracking is available at `GET /api/shipments/track/{code}`.
5. **Review**: once the order is `DELIVERED`, the buyer may review the product
   (`POST /api/products/{id}/reviews`). The seller's `reputation_score` is
   recalculated as the average of all their products' review ratings.

## Where the AI connects

`POST /api/chat` → `services/ai_chat.py`:

1. If an `order_id` is passed, the service loads the **real** order, items, and
   shipment and formats them into a context block.
2. It builds a system prompt that instructs the assistant to act as store
   support, answer using **only** that context (status, ETA, simplified return
   policy), never fabricate order data, and escalate to a human when unsure.
3. It calls the Anthropic Messages API (`claude-sonnet-4-6`) with recent history,
   persists both the user turn and the assistant reply as `ChatMessage`s, and
   returns the reply.
4. If no API key is configured, it returns a helpful offline response that still
   includes the real order context — so the feature is always demonstrable.

## Key decisions & trade-offs (MVP)

| Decision | Rationale / trade-off |
| --- | --- |
| **SQLModel** (SQLAlchemy 2 + Pydantic v2) | One class for ORM + schema where they coincide; separate Pydantic DTOs where they don't. |
| **Schema bootstrap via `create_all` on startup** | Single `docker compose up` with no migration step in the loop. Alembic is included (`alembic/`) for versioned production changes. |
| **Startup seed in the lifespan** | Guarantees a demonstrable dataset on first boot; idempotent (skips if users exist). |
| **Prices in integer cents** | Avoids float rounding across cart/checkout/reporting. |
| **Price/title snapshot on `OrderItem`** | Later catalog edits never rewrite historical orders. |
| **Mock payment & shipping** | Keeps the MVP self-contained; both are single-class interfaces ready for a real provider. |
| **Generated Angular client** | Contract lives in the backend; the front never duplicates or drifts from DTOs. |
| **Access token in memory/localStorage; refresh in httpOnly cookie** | Refresh token is not readable by JS; the interceptor transparently refreshes on 401. |
| **No Redis/queue/storage in the MVP** | Fewer moving parts. These are the first roadmap items. |
