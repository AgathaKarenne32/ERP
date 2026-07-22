# Roadmap

The MVP is a complete-but-minimal skeleton. These are the natural next steps,
roughly in priority order. The first two are the "Entrega 2" items whose
interfaces already exist in the codebase.

## 1. Real payment gateway (Mercado Pago / Stripe)
- Implement `services/payment.py`'s `PaymentService` interface against a real
  provider (create preference/intent, redirect/checkout, confirm).
- Handle **webhooks** for async payment confirmation instead of the current
  synchronous mock; move the order to `PAID` on the webhook.
- Add idempotency keys and store the provider transaction id on the order.

## 2. Image storage (S3 / Cloudflare R2)
- Replace the "image URL" field with real uploads: presigned PUT from the
  browser, store object keys, serve via CDN.
- Add image validation, resizing/thumbnails.

## 3. Advanced search
- Move from `ILIKE` to Postgres full-text search (`tsvector` + GIN index) with
  ranking; later, Elasticsearch/OpenSearch or Typesense if needed.
- Facets (category counts, price histograms), sorting, relevance.

## 4. Async work queues (Celery / RQ)
- Offload email (order confirmation, shipping updates), review requests, and
  reputation recomputation to background workers.
- Add a broker (Redis/RabbitMQ) to compose.

## 5. Real carrier integration
- Replace the mock shipment flow with a carrier API (Correios/transportadora):
  label generation, real tracking events, webhooks.

## 6. Caching (Redis)
- Cache the public catalog/product pages and search results.
- Rate-limit the AI chat and auth endpoints.

## 7. AI chat: streaming + human handoff
- Stream tokens to the widget (SSE/WebSocket) for a live typing experience.
- Detect low-confidence/escalation intents and route to a human inbox.
- Tools/function-calling so the assistant can take actions (open a return,
  re-send tracking) instead of only reading context.

## 8. Admin panel
- Moderation (products, reviews), user/seller management, dispute handling,
  platform-wide metrics.

## 9. Testing & load
- Broaden backend coverage (unit tests per service, permission edge cases).
- More frontend component/e2e tests (Playwright) for the buy/sell journeys.
- Load testing (k6/Locust) on search + checkout; tune DB indexes and workers.

## 10. Security hardening
- Refresh-token rotation + revocation list; short access-token lifetimes.
- Per-endpoint rate limiting and abuse protection.
- Input/output audit, dependency scanning, secret scanning in CI.
- Fine-grained authorization tests; CSRF review for cookie flows.

## Smaller follow-ups
- Order cancellation / refunds (wire `payment_status=REFUNDED`).
- Wishlist / favorites; multiple addresses; shipping cost calculation.
- Seller onboarding & payouts.
- i18n / currency beyond BRL.
- Pagination + infinite scroll polish; skeleton loaders.
