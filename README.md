# MercadoMVP — E-commerce Marketplace (MVP)

A minimal but **end-to-end** marketplace, inspired in spirit by Mercado Livre:
from listing a product to buying, shipping, tracking, and reviewing it — plus an
AI customer-support assistant. Built as a solid, typed, dockerized foundation
that is easy to extend.

- **Backend:** Python 3.12 · FastAPI · SQLModel · PostgreSQL · JWT auth · Anthropic AI
- **Frontend:** Angular 18 (standalone + signals) · Tailwind · Angular Material · typed client generated from OpenAPI
- **Infra:** Docker Compose (`db` + `backend` + `frontend`)

> The companion docs: [ARCHITECTURE.md](./ARCHITECTURE.md) ·
> [DEPLOY.md](./DEPLOY.md) · [ROADMAP.md](./ROADMAP.md)

---

## Quick start (Docker)

```bash
cp .env.example .env          # tweak secrets if you like
docker compose up --build
```

Then open:

| Service            | URL                            |
| ------------------ | ------------------------------ |
| Frontend (Angular) | http://localhost:4200          |
| Backend (API)      | http://localhost:8000/api      |
| Swagger docs       | http://localhost:8000/docs     |
| OpenAPI schema     | http://localhost:8000/openapi.json |

On first boot the backend **creates the schema and seeds demo data**
automatically (via the FastAPI lifespan), so the full flow is demonstrable
without registering anything by hand.

### Demo credentials

All demo users share the password **`demo1234`**.

| Role   | Email               | Notes                                             |
| ------ | ------------------- | ------------------------------------------------- |
| Buyer  | `buyer@demo.com`    | Has one already-**delivered** order (review it!)  |
| Seller | `seller1@demo.com`  | Store **TechStore** (5 products)                  |
| Seller | `seller2@demo.com`  | Store **Casa & Conforto** (5 products)            |

---

## Running in dev (without Docker)

**Backend** (Python 3.11+, [uv](https://github.com/astral-sh/uv)):

```bash
cd backend
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
# Point at a local Postgres, or use SQLite for a zero-dependency run:
export DATABASE_URL="sqlite:///./dev.db"
uvicorn app.main:app --reload
```

**Frontend** (Node 20+):

```bash
cd frontend
npm install
# (Re)generate the typed API client from the running backend or the committed spec:
npm run gen:api                                   # uses frontend/openapi.json
# or: ./gen-api.sh http://localhost:8000/openapi.json
ng serve
```

The generated client lives in `src/app/core/api/` — **never hand-write DTOs**;
regenerate from the backend's OpenAPI instead.

---

## Testing & quality

```bash
# Backend: end-to-end integration test (login → product → checkout → ship → review)
cd backend && source .venv/bin/activate
pytest -q
ruff check app tests && black --check app tests

# Frontend: render tests for key screens
cd frontend && npm test
```

---

## Project structure

```
.
├── backend/                    # FastAPI service
│   ├── app/
│   │   ├── main.py             # app, routers, CORS, lifespan (schema + seed)
│   │   ├── core/               # config, db, security (JWT), auth deps
│   │   ├── models/             # SQLModel tables (user, product, order, …)
│   │   ├── schemas/            # Pydantic request/response DTOs
│   │   ├── routers/            # auth, products, cart, orders, shipping, reviews, seller, chat
│   │   ├── services/           # checkout, payment (mock), shipping (mock), ai_chat
│   │   └── seed.py             # demo data
│   ├── alembic/                # migrations
│   └── tests/                  # pytest + httpx e2e
├── frontend/                   # Angular 18 standalone SPA
│   ├── src/app/
│   │   ├── core/               # auth service/guard/interceptor, api/ (generated)
│   │   ├── shared/             # product card, cents pipe
│   │   └── features/           # home, search, product, cart, checkout, orders, auth, seller, chat
│   ├── gen-api.sh              # OpenAPI → typescript-angular client
│   └── Dockerfile              # ng serve (dev) / Nginx (prod)
├── docker-compose.yml          # dev stack
├── docker-compose.prod.yml     # prod stack (Nginx + uvicorn workers)
└── .env.example
```

---

## The AI assistant

The floating chat widget (bottom-right, for logged-in buyers) calls
`POST /api/chat`. The backend `ai_chat` service builds a **real** context from
the buyer's order/shipment data and instructs Claude
(`claude-sonnet-4-6`) to answer only from that context — never inventing order
facts — and to escalate to a human when unsure. The `ANTHROPIC_API_KEY` stays
server-side only. Without a key, the chat runs in an offline demo mode that
still surfaces the real order data, so the flow always works.

---

## Notes on MVP scope

Payment and product images are intentionally simplified (mock gateway, image
URLs). Both interfaces are structured so a real payment provider (Mercado
Pago/Stripe) and object storage (S3/R2) can be dropped in later — see
[ROADMAP.md](./ROADMAP.md).
