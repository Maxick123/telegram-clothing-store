# Telegram Clothing Store Production Program Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a locally deployable production-grade Telegram clothing store with a web CRM, commerce, support, marketing and operations features.

**Architecture:** A FastAPI modular monolith exposes REST and WebSocket contracts to an Aiogram bot and a Next.js CRM. PostgreSQL is the system of record; Redis backs Celery and transient coordination. Docker Compose runs every service locally, while integrations are isolated behind adapters.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Pydantic, Aiogram 3, PostgreSQL, Redis, Celery, Next.js/React/TypeScript, TanStack Query, Docker Compose, Nginx, Pytest, Playwright, ЮKassa test API.

## Global Constraints

- Run all services locally through Docker Compose; no secret is committed to Git.
- Use PostgreSQL for persistent business data and Redis only for transient state, cache, broker and locks.
- Bot and CRM call the backend API; neither accesses the database directly.
- Store money as integer kopecks and snapshot order-line product data at checkout.
- Treat inventory mutation, reservation release and payment webhook processing as idempotent transactions.
- Enforce authorization in backend service methods as well as HTTP endpoints.
- Preserve commercial history with archive/soft-delete semantics and immutable audit records.
- Use a test ЮKassa shop/key pair only from `.env`; validate every incoming webhook.
- Support Russian customer-facing copy and Moscow timezone defaults; store timestamps in UTC.
- Every task below ends with its stated automated check and a focused Git commit.

---

## Repository map

| Area | Responsibility |
| --- | --- |
| `infra/` | Compose, Nginx, Postgres backup, container build files and local commands |
| `backend/app/core/` | config, DB/session, security, RBAC, errors and audit plumbing |
| `backend/app/modules/` | bounded domains: identity, catalog, inventory, commerce, CRM, messaging, marketing, returns, analytics |
| `backend/app/api/` | versioned HTTP/WebSocket routers and request/response schemas |
| `backend/tests/` | unit, API and integration tests grouped by module |
| `bot/app/` | bot routers, keyboards, FSM, media bridge and administrator-group callbacks |
| `admin-web/src/` | CRM routes, components, API client, WebSocket client and role-aware UI |
| `docs/` | operator runbook, API contracts, deployment and recovery documentation |

## Milestone 1 — Platform, security and catalogue

### Task 1: Bootstrap the local stack and configuration contract

**Files:**
- Create: `compose.yaml`, `.env.example`, `.gitignore`, `infra/nginx/nginx.conf`
- Create: `backend/Dockerfile`, `bot/Dockerfile`, `admin-web/Dockerfile`, `infra/postgres/backup.sh`
- Create: `docs/run-local.md`
- Test: `infra/tests/test_compose_config.ps1`

**Produces:** Compose services `postgres`, `redis`, `backend`, `bot`, `worker`, `admin-web`, `nginx`; environment variables `DATABASE_URL`, `REDIS_URL`, `TELEGRAM_BOT_TOKEN`, `YOOKASSA_SHOP_ID`, `YOOKASSA_SECRET_KEY`, `JWT_SECRET` and `BACKUP_RETENTION_DAYS`.

- [ ] **Step 1: Write the failing configuration test.**

```powershell
$cfg = docker compose config
foreach ($service in 'postgres','redis','backend','bot','worker','admin-web','nginx') {
  if ($cfg -notmatch "(?m)^\s{2}$service:") { throw "missing $service" }
}
if ((Get-Content .gitignore -Raw) -notmatch '\.env') { throw '.env must be ignored' }
```

- [ ] **Step 2: Run it to verify it fails.**

Run: `pwsh infra/tests/test_compose_config.ps1`  
Expected: failure because Compose files do not exist.

- [ ] **Step 3: Create Compose, Dockerfiles, example environment, health checks and the seven-day rotating backup script.**

```yaml
services:
  postgres:
    image: postgres:16-alpine
    healthcheck: { test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER"], interval: 10s, timeout: 5s, retries: 5 }
  redis:
    image: redis:7-alpine
  backend:
    depends_on: { postgres: { condition: service_healthy }, redis: { condition: service_started } }
```

- [ ] **Step 4: Verify configuration and container health.**

Run: `pwsh infra/tests/test_compose_config.ps1; docker compose up -d; docker compose ps`  
Expected: configuration passes and all services become healthy/running.

- [ ] **Step 5: Commit.**

Run: `git add compose.yaml .env.example .gitignore infra backend/Dockerfile bot/Dockerfile admin-web/Dockerfile docs/run-local.md && git commit -m "chore: bootstrap local commerce stack"`

### Task 2: Establish backend foundation, staff identity and RBAC

**Files:**
- Create: `backend/app/main.py`, `backend/app/core/{config,db,security,errors}.py`
- Create: `backend/app/modules/identity/{models,schemas,service,router}.py`
- Create: `backend/alembic/versions/001_identity.py`
- Test: `backend/tests/identity/test_auth_api.py`

**Interfaces:** Produces `POST /api/v1/auth/login`, `POST /api/v1/auth/refresh`, `GET /api/v1/auth/me`; `require_permission(permission: str)` and roles Administrator, OrdersManager, SupportOperator, ContentManager.

- [ ] **Step 1: Write failing API tests for password login and forbidden access.**

```python
def test_content_manager_cannot_change_order_status(client, content_token):
    response = client.patch('/api/v1/orders/1/status', headers=content_token, json={'status_code': 'paid'})
    assert response.status_code == 403

def test_login_sets_refresh_cookie(client, staff_user):
    response = client.post('/api/v1/auth/login', json={'login': staff_user.login, 'password': 'correct-password'})
    assert response.status_code == 200
    assert 'refresh_token' in response.cookies
```

- [ ] **Step 2: Run the identity test.**

Run: `docker compose exec backend pytest tests/identity/test_auth_api.py -v`  
Expected: failure because routes are absent.

- [ ] **Step 3: Implement Argon2 password hashing, rotating refresh tokens, permissions and Alembic migration.**

```python
def require_permission(permission: str):
    async def dependency(actor: Staff = Depends(current_staff)) -> Staff:
        if permission not in actor.permission_codes:
            raise HTTPException(status_code=403, detail='permission_denied')
        return actor
    return dependency
```

- [ ] **Step 4: Apply migration and run tests.**

Run: `docker compose exec backend alembic upgrade head; docker compose exec backend pytest tests/identity/test_auth_api.py -v`  
Expected: migration and tests pass.

- [ ] **Step 5: Commit.**

Run: `git add backend && git commit -m "feat: add staff authentication and permissions"`

### Task 3: Implement catalogue, media and inventory variants

**Files:**
- Create: `backend/app/modules/catalog/{models,schemas,service,router}.py`
- Create: `backend/app/modules/inventory/{models,service,router}.py`
- Create: `backend/alembic/versions/002_catalog_inventory.py`
- Test: `backend/tests/catalog/test_variants_api.py`, `backend/tests/inventory/test_stock_service.py`

**Interfaces:** Produces product/category/collection CRUD, `ProductVariant(product_id, color, size, stock_on_hand, stock_reserved)`, and `available_quantity(variant_id) -> int`.

- [ ] **Step 1: Write failing stock and product tests.**

```python
def test_available_quantity_subtracts_active_reservations(variant):
    variant.stock_on_hand = 7
    variant.stock_reserved = 3
    assert available_quantity(variant) == 4

def test_product_variant_requires_unique_color_and_size(client, admin_token, product):
    payload = {'color': 'Black', 'size': 'M', 'sku': 'HD-BLK-M', 'stock_on_hand': 2, 'price_kopecks': 599000}
    assert client.post(f'/api/v1/products/{product.id}/variants', headers=admin_token, json=payload).status_code == 201
    assert client.post(f'/api/v1/products/{product.id}/variants', headers=admin_token, json=payload).status_code == 409
```

- [ ] **Step 2: Run the tests to verify failure.**

Run: `docker compose exec backend pytest tests/catalog/test_variants_api.py tests/inventory/test_stock_service.py -v`  
Expected: failure because models and routes are absent.

- [ ] **Step 3: Implement entities, archive flag, media ordering, inventory movements and optimistic stock checks.**

```python
def available_quantity(variant: ProductVariant) -> int:
    return variant.stock_on_hand - variant.stock_reserved
```

- [ ] **Step 4: Run migrations and tests.**

Run: `docker compose exec backend alembic upgrade head; docker compose exec backend pytest tests/catalog tests/inventory -v`  
Expected: pass.

- [ ] **Step 5: Commit.**

Run: `git add backend && git commit -m "feat: add catalogue variants and inventory"`

## Milestone 2 — Customer commerce and ЮKassa

### Task 4: Add customers, favourites, carts and validated pricing

**Files:**
- Create: `backend/app/modules/customers/{models,schemas,service,router}.py`
- Create: `backend/app/modules/commerce/{cart_models,cart_service,cart_router}.py`
- Create: `backend/alembic/versions/003_customers_carts.py`
- Test: `backend/tests/commerce/test_cart_pricing.py`

**Interfaces:** Produces customer upsert by Telegram ID, `POST /api/v1/carts/items`, `PATCH /api/v1/carts/items/{id}`, `POST /api/v1/favorites/{product_id}` and `quote_cart(cart_id) -> CartQuote`.

- [ ] **Step 1: Write a failing price integrity test.**

```python
def test_quote_uses_server_variant_price_not_client_price(cart, black_m_variant):
    add_item(cart, black_m_variant.id, quantity=2)
    black_m_variant.price_kopecks = 599000
    quote = quote_cart(cart.id)
    assert quote.subtotal_kopecks == 1_198_000
```

- [ ] **Step 2: Run it.**

Run: `docker compose exec backend pytest tests/commerce/test_cart_pricing.py -v`  
Expected: failure.

- [ ] **Step 3: Implement customer profile, favourite uniqueness, cart item limits and server-side pricing.**

```python
def quote_cart(cart_id: UUID) -> CartQuote:
    items = cart_repository.lock_items(cart_id)
    return CartQuote(subtotal_kopecks=sum(item.variant.current_price_kopecks * item.quantity for item in items))
```

- [ ] **Step 4: Run cart and customer tests.**

Run: `docker compose exec backend pytest tests/commerce tests/customers -v`  
Expected: pass.

- [ ] **Step 5: Commit.**

Run: `git add backend && git commit -m "feat: add customer carts and favorites"`

### Task 5: Add promo codes, discounts, orders and stock reservations

**Files:**
- Create: `backend/app/modules/marketing/{models,service,router}.py`
- Create: `backend/app/modules/commerce/{order_models,order_service,order_router,reservation_tasks}.py`
- Create: `backend/alembic/versions/004_orders_marketing.py`
- Test: `backend/tests/commerce/test_checkout_reservation.py`, `backend/tests/marketing/test_promo_rules.py`

**Interfaces:** Produces `POST /api/v1/checkout`, `POST /api/v1/carts/{id}/promo`, `release_expired_reservations() -> int`, order status workflow and immutable `OrderItemSnapshot`.

- [ ] **Step 1: Write failing reservation and snapshot tests.**

```python
def test_checkout_reserves_stock_and_snapshots_price(cart, variant):
    variant.stock_on_hand = 1
    order = checkout(cart.id, recipient=recipient(), delivery=pickup())
    assert variant.stock_reserved == 1
    assert order.items[0].unit_price_kopecks == variant.current_price_kopecks

def test_expired_reservation_is_released(expired_order, variant):
    assert release_expired_reservations(now=expired_order.reserve_until) == 1
    assert variant.stock_reserved == 0
```

- [ ] **Step 2: Run the tests.**

Run: `docker compose exec backend pytest tests/commerce/test_checkout_reservation.py tests/marketing/test_promo_rules.py -v`  
Expected: failure.

- [ ] **Step 3: Implement locked checkout transaction, percentage/fixed promo constraints and scheduled expiry task.**

```python
with session.begin():
    variant = variants.lock_for_update(item.variant_id)
    if variant.stock_on_hand - variant.stock_reserved < item.quantity:
        raise OutOfStock(item.variant_id)
    variant.stock_reserved += item.quantity
```

- [ ] **Step 4: Run migrations and tests.**

Run: `docker compose exec backend alembic upgrade head; docker compose exec backend pytest tests/commerce tests/marketing -v`  
Expected: pass.

- [ ] **Step 5: Commit.**

Run: `git add backend && git commit -m "feat: add checkout reservations and promotions"`

### Task 6: Integrate ЮKassa test payments with idempotent webhooks

**Files:**
- Create: `backend/app/modules/payments/{provider,service,router}.py`
- Create: `backend/app/modules/payments/yookassa_provider.py`
- Modify: `backend/app/modules/commerce/order_service.py`
- Test: `backend/tests/payments/test_yookassa_webhook.py`

**Interfaces:** Produces `PaymentProvider.create_payment(order) -> PaymentRedirect`, `POST /api/v1/payments/yookassa/webhook`, and payment states `pending`, `succeeded`, `canceled`, `failed`.

- [ ] **Step 1: Write failing duplicate-webhook test.**

```python
def test_succeeded_webhook_is_idempotent(client, pending_payment, signed_event):
    first = client.post('/api/v1/payments/yookassa/webhook', json=signed_event)
    second = client.post('/api/v1/payments/yookassa/webhook', json=signed_event)
    assert first.status_code == second.status_code == 200
    assert pending_payment.order.stock_commit_count == 1
```

- [ ] **Step 2: Run it.**

Run: `docker compose exec backend pytest tests/payments/test_yookassa_webhook.py -v`  
Expected: failure.

- [ ] **Step 3: Implement provider adapter, metadata correlation, signature/identity validation and transactionally committed reservations.**

```python
class PaymentProvider(Protocol):
    async def create_payment(self, order: Order) -> PaymentRedirect:
        raise NotImplementedError

    async def verify_event(self, payload: dict[str, object]) -> ProviderEvent:
        raise NotImplementedError
```

- [ ] **Step 4: Run payment tests.**

Run: `docker compose exec backend pytest tests/payments -v`  
Expected: pass.

- [ ] **Step 5: Commit.**

Run: `git add backend && git commit -m "feat: integrate yookassa test payments"`

## Milestone 3 — Telegram buyer flow and CRM foundation

### Task 7: Implement the Aiogram customer storefront

**Files:**
- Create: `bot/app/{main,api_client,config}.py`
- Create: `bot/app/routers/{start,catalog,cart,checkout,orders,profile}.py`
- Create: `bot/app/keyboards/{main_menu,catalog,cart}.py`
- Test: `bot/tests/test_catalog_router.py`, `bot/tests/test_checkout_fsm.py`

**Interfaces:** Bot calls public customer API with `telegram_id`; buyer menus include catalogue, new items, discounts, favourites, cart, orders, support and profile.

- [ ] **Step 1: Write failing FSM and callback tests.**

```python
async def test_checkout_collects_recipient_before_delivery(dispatcher, update):
    await dispatcher.feed_update(bot, update('/checkout'))
    assert await state.get_state() == CheckoutState.recipient_first_name
```

- [ ] **Step 2: Run bot tests.**

Run: `docker compose exec bot pytest tests/test_catalog_router.py tests/test_checkout_fsm.py -v`  
Expected: failure.

- [ ] **Step 3: Implement API client, callback payload signing, variant picker, cart controls and checkout FSM.**

```python
class CheckoutState(StatesGroup):
    recipient_first_name = State()
    recipient_last_name = State()
    phone = State()
    delivery_method = State()
    address = State()
    confirmation = State()
```

- [ ] **Step 4: Run bot tests.**

Run: `docker compose exec bot pytest -v`  
Expected: pass.

- [ ] **Step 5: Commit.**

Run: `git add bot && git commit -m "feat: add telegram shopping flow"`

### Task 8: Implement CRM shell, product and order operations

**Files:**
- Create: `admin-web/src/app/{login,products,orders,customers}/page.tsx`
- Create: `admin-web/src/lib/{api,auth,permissions}.ts`
- Create: `admin-web/src/components/{AppShell,DataTable,StatusBadge}.tsx`
- Test: `admin-web/src/**/*.test.tsx`, `admin-web/e2e/orders.spec.ts`

**Interfaces:** Produces role-aware navigation; product CRUD, archive and stock editor; order list/detail/status transition UI; customer list/detail UI.

- [ ] **Step 1: Write a failing role-navigation test.**

```tsx
it('hides catalog navigation from a support operator', () => {
  render(<AppShell permissions={['conversations.read']} />)
  expect(screen.queryByRole('link', { name: 'Товары' })).not.toBeInTheDocument()
})
```

- [ ] **Step 2: Run frontend tests.**

Run: `docker compose exec admin-web npm test -- --run`  
Expected: failure.

- [ ] **Step 3: Implement authenticated API client, protected routes and responsive CRM screens.**

```ts
export const can = (permissions: string[], permission: string) => permissions.includes(permission) || permissions.includes('*')
```

- [ ] **Step 4: Run unit and browser test.**

Run: `docker compose exec admin-web npm test -- --run; docker compose exec admin-web npm run test:e2e -- orders.spec.ts`  
Expected: pass.

- [ ] **Step 5: Commit.**

Run: `git add admin-web && git commit -m "feat: add crm catalog and order management"`

## Milestone 4 — Unified support and notifications

### Task 9: Build conversations, attachments and WebSocket delivery

**Files:**
- Create: `backend/app/modules/messaging/{models,schemas,service,router,websocket}.py`
- Create: `backend/alembic/versions/005_messaging.py`
- Create: `admin-web/src/app/chats/page.tsx`, `admin-web/src/lib/realtime.ts`
- Test: `backend/tests/messaging/test_conversation_events.py`, `admin-web/src/app/chats/page.test.tsx`

**Interfaces:** `POST /api/v1/conversations/{id}/messages`, `GET /api/v1/conversations`, `WS /api/v1/ws/conversations`; message fields include `channel`, `author_type`, `author_id`, `telegram_message_id`, `delivery_status`, `attachments`.

- [ ] **Step 1: Write the failing delivery event test.**

```python
async def test_inbound_message_is_persisted_before_websocket_event(event_bus, customer):
    message = await receive_customer_message(customer.id, text='Где заказ?')
    event = await event_bus.next('conversation.updated')
    assert event.message_id == message.id
    assert repository.get_message(message.id).text == 'Где заказ?'
```

- [ ] **Step 2: Run it.**

Run: `docker compose exec backend pytest tests/messaging/test_conversation_events.py -v`  
Expected: failure.

- [ ] **Step 3: Implement conversation locking, media metadata, persisted delivery states and authenticated WebSocket fan-out.**

```python
await message_repository.create(
    conversation_id=conversation.id,
    author_type=AuthorType.CUSTOMER,
    text=incoming.text,
    channel=MessageChannel.TELEGRAM,
)
await session.commit()
await event_bus.publish('conversation.updated', ConversationEvent.from_message(message))
```

- [ ] **Step 4: Run backend and CRM chat tests.**

Run: `docker compose exec backend pytest tests/messaging -v; docker compose exec admin-web npm test -- --run page.test.tsx`  
Expected: pass.

- [ ] **Step 5: Commit.**

Run: `git add backend admin-web && git commit -m "feat: add realtime customer conversations"`

### Task 10: Mirror support messages to the operator group and enforce reply binding

**Files:**
- Create: `bot/app/routers/{support,operator_group}.py`
- Create: `bot/app/services/media_bridge.py`
- Modify: `backend/app/modules/messaging/service.py`
- Test: `bot/tests/test_operator_reply_binding.py`, `backend/tests/messaging/test_group_mirror.py`

**Interfaces:** Group callback payload contains signed `conversation_id`; `reply_from_operator(conversation_id, staff_id, text, attachments)` rejects a staff member without `conversations.reply`.

- [ ] **Step 1: Write failing wrong-conversation test.**

```python
async def test_group_reply_uses_callback_conversation_not_replied_message_text(operator, conversation_a, conversation_b):
    result = await handle_operator_callback(operator, f'reply:{conversation_a.id}', 'Ответ')
    assert result.conversation_id == conversation_a.id
    assert not repository.has_message(conversation_b.id, 'Ответ')
```

- [ ] **Step 2: Run it.**

Run: `docker compose exec bot pytest tests/test_operator_reply_binding.py -v`  
Expected: failure.

- [ ] **Step 3: Implement group mirror cards, callback verification, operator assignment and client delivery through the bot.**

```python
callback_data = operator_callback.pack(action='reply', conversation_id=conversation.id, nonce=message.nonce)
```

- [ ] **Step 4: Run messaging and bot tests.**

Run: `docker compose exec bot pytest tests/test_operator_reply_binding.py -v; docker compose exec backend pytest tests/messaging/test_group_mirror.py -v`  
Expected: pass.

- [ ] **Step 5: Commit.**

Run: `git add bot backend && git commit -m "feat: mirror support conversations to operator group"`

## Milestone 5 — Marketing, returns, analytics and operations

### Task 11: Add mailings, segmentation and trigger automations

**Files:**
- Create: `backend/app/modules/marketing/{mailing_models,mailing_service,automation_tasks}.py`
- Create: `admin-web/src/app/mailings/page.tsx`
- Test: `backend/tests/marketing/test_mailing_segments.py`, `backend/tests/marketing/test_abandoned_cart_task.py`

**Interfaces:** `resolve_audience(segment: AudienceSegment) -> list[UUID]`; delayed mailing states `draft`, `scheduled`, `sending`, `completed`, `failed`; abandonment trigger threshold configured in settings.

- [ ] **Step 1: Write failing segment test.**

```python
def test_vip_segment_includes_tagged_customers_only(db, vip_customer, regular_customer):
    assert resolve_audience(AudienceSegment(tag='VIP')) == [vip_customer.id]
```

- [ ] **Step 2: Run it.**

Run: `docker compose exec backend pytest tests/marketing/test_mailing_segments.py tests/marketing/test_abandoned_cart_task.py -v`  
Expected: failure.

- [ ] **Step 3: Implement audience query, throttled Celery delivery, delivery statistics and explicit opt-out settings.**

```python
@shared_task(bind=True, autoretry_for=(TransientTelegramError,), retry_backoff=True, max_retries=3)
def send_mailing_recipient(self, mailing_id: str, customer_id: str) -> None:
    deliver_mailing_recipient(UUID(mailing_id), UUID(customer_id))
```

- [ ] **Step 4: Run marketing tests.**

Run: `docker compose exec backend pytest tests/marketing -v`  
Expected: pass.

- [ ] **Step 5: Commit.**

Run: `git add backend admin-web && git commit -m "feat: add mailings and marketing automations"`

### Task 12: Add returns, dashboard analytics and stock alerts

**Files:**
- Create: `backend/app/modules/returns/{models,service,router}.py`
- Create: `backend/app/modules/analytics/{service,router}.py`
- Create: `backend/app/modules/inventory/alert_tasks.py`
- Create: `admin-web/src/app/{returns,analytics}/page.tsx`
- Test: `backend/tests/returns/test_return_workflow.py`, `backend/tests/analytics/test_dashboard_metrics.py`

**Interfaces:** Return statuses `new`, `reviewing`, `approved`, `rejected`, `received`, `refunded`; `GET /api/v1/analytics/dashboard?from=&to=`; low-stock threshold per variant.

- [ ] **Step 1: Write failing return and revenue tests.**

```python
def test_return_cannot_move_from_new_to_refunded(return_request):
    with pytest.raises(InvalidReturnTransition):
        change_return_status(return_request.id, 'refunded')

def test_dashboard_revenue_excludes_cancelled_orders(db, paid_order, cancelled_order):
    assert dashboard_metrics(period()).revenue_kopecks == paid_order.total_kopecks
```

- [ ] **Step 2: Run them.**

Run: `docker compose exec backend pytest tests/returns/test_return_workflow.py tests/analytics/test_dashboard_metrics.py -v`  
Expected: failure.

- [ ] **Step 3: Implement workflow validation, aggregate queries, daily low-stock task and CRM charts.**

```python
ALLOWED_RETURN_TRANSITIONS = {'new': {'reviewing'}, 'reviewing': {'approved', 'rejected'}, 'approved': {'received'}, 'received': {'refunded'}}
```

- [ ] **Step 4: Run tests.**

Run: `docker compose exec backend pytest tests/returns tests/analytics tests/inventory -v`  
Expected: pass.

- [ ] **Step 5: Commit.**

Run: `git add backend admin-web && git commit -m "feat: add returns analytics and stock alerts"`

### Task 13: Finalise audits, backups, security checks and production documentation

**Files:**
- Create: `backend/app/modules/audit/{models,service}.py`
- Create: `infra/scripts/{backup,restore,smoke-test}.ps1`
- Create: `docs/{operator-runbook,backup-recovery,security,telegram-setup}.md`
- Modify: `compose.yaml`, `docs/run-local.md`
- Test: `backend/tests/audit/test_audit_log.py`, `infra/tests/test_backup_restore.ps1`

**Interfaces:** `audit.log(actor, action, entity_type, entity_id, before, after)` and documented restore command accepting one backup path.

- [ ] **Step 1: Write failing audit and backup test.**

```python
def test_price_change_creates_immutable_audit_record(admin, product):
    update_product_price(admin, product.id, 549000)
    row = latest_audit()
    assert row.action == 'product.price_changed'
    assert row.before['price_kopecks'] == 599000
```

- [ ] **Step 2: Run checks.**

Run: `docker compose exec backend pytest tests/audit/test_audit_log.py -v; pwsh infra/tests/test_backup_restore.ps1`  
Expected: failure.

- [ ] **Step 3: Implement append-only audit writes, backup/restore scripts, health endpoints and security/runbook documentation.**

```python
def log(actor: Staff, action: str, entity_type: str, entity_id: UUID, before: dict, after: dict) -> AuditLog:
    return AuditLog(actor_id=actor.id, action=action, entity_type=entity_type, entity_id=entity_id, before=before, after=after)
```

- [ ] **Step 4: Verify restore in an isolated local database and run the full suite.**

Run: `pwsh infra/tests/test_backup_restore.ps1; docker compose exec backend pytest -v; docker compose exec bot pytest -v; docker compose exec admin-web npm test -- --run`  
Expected: all checks pass.

- [ ] **Step 5: Commit.**

Run: `git add backend infra compose.yaml docs && git commit -m "chore: complete operational safeguards"`

## Final release gate

- [ ] Run migrations from an empty PostgreSQL volume and seed the first administrator.
- [ ] Use a Telegram test account to complete a real end-to-end order and a ЮKassa test payment.
- [ ] Verify an out-of-stock variant cannot be purchased concurrently by two sessions.
- [ ] Verify an inbound media message appears in CRM and the operator group; reply from each channel reaches the same customer conversation.
- [ ] Verify a scheduled mailing, abandoned-cart trigger, low-stock notification, audit row and backup/restore cycle.
- [ ] Run `docker compose config`, backend Pytest suite, bot Pytest suite, frontend unit tests and Playwright e2e tests.
- [ ] Tag the release only after all commands above pass and the operator runbook matches the running Compose stack.

## Coverage check

| Specification area | Plan tasks |
| --- | --- |
| Local Docker, Nginx, Redis, PostgreSQL, backups | 1, 13 |
| Staff, roles, permissions, security, audit | 2, 13 |
| Categories, collections, products, media, variants, stock | 3, 8 |
| Customer profiles, favourites, addresses, carts | 4, 7, 8 |
| Checkout, promo codes, discounts, reserves, orders | 5, 6, 7, 8 |
| ЮKassa and status notifications | 6, 7, 10 |
| CRM and customers | 8 |
| Realtime two-way support and Telegram operator group | 9, 10 |
| Mailings, scheduled jobs and automation | 11 |
| Returns, analytics, low-stock notifications | 12 |
| Operational quality and release verification | 13, final gate |
