# Invoice Generator with Payment-Reminder Engine — Implementation Plan

Source of truth: `invoice-reminder-spec.md` (Sections 10-13), `openspec/changes/add-invoice-reminder-v1/{proposal,design,tasks}.md`, and all 7 spec files under `openspec/changes/add-invoice-reminder-v1/specs/*/spec.md`. This is a greenfield build — the repo currently has no Python backend code.

---

## 1. Repo Layout

All backend code lives under a new top-level `backend/` directory (keeps the existing `openspec/`, `node_modules/`, spec docs untouched at repo root, and leaves room for a future `frontend/`).

```
backend/
  pyproject.toml                 # single source of dependency truth (Poetry or PEP 621 + pip-tools); pin fastapi, sqlalchemy, alembic, celery, redis, pydantic, psycopg, passlib[bcrypt] or argon2-cffi, python-jose or itsdangerous for sessions, pytz/zoneinfo, pytest, pytest-asyncio, factory_boy, hypothesis, httpx
  alembic.ini
  .env.example                   # DATABASE_URL, REDIS_URL, SECRET_KEY, EMAIL_PROVIDER creds, REMINDER_KILL_SWITCH default
  docker-compose.yml              # postgres, redis (see Section 10)
  app/
    __init__.py
    main.py                      # FastAPI app factory, router registration, middleware wiring
    config.py                    # pydantic-settings Settings object, loads .env
    db/
      __init__.py
      session.py                 # engine, SessionLocal, get_db dependency
      base.py                    # declarative Base, import hub for all models (used by Alembic env.py)
    models/
      __init__.py
      customer.py
      tax_rate.py
      invoice.py
      invoice_line_item.py
      payment.py
      reminder_rule.py
      reminder_instance.py
      audit_log.py
      user.py
      mixins.py                  # TimestampMixin (created_at/updated_at)
    schemas/
      __init__.py
      customer.py
      invoice.py
      payment.py
      reminder.py
      tax_rate.py
      audit.py
      user.py
      dashboard.py
      reports.py
      common.py                  # shared pagination envelope, error envelope
    core/
      security.py                 # password hashing (argon2/bcrypt), session/token issuance+verification
      permissions.py               # RBAC dependency: require_role(*roles)
      rounding.py                  # round_half_up(Decimal) -> Decimal, quantize to 2dp
      timezone.py                  # to_ist(), ist_end_of_day(date) -> UTC datetime, now_utc()
      exceptions.py                 # domain exception classes (OverpaymentError, EditBelowPaymentsError, etc.) + FastAPI exception handlers mapping them to HTTP codes
    services/                     # business-rule layer — pure(ish) functions operating on SQLAlchemy session, no HTTP concerns
      __init__.py
      customers.py
      invoices.py
      payments.py
      reminders.py
      tax_rates.py
      audit.py
      reports.py
      dashboard.py
      auth.py
    api/
      __init__.py
      deps.py                     # get_current_user, get_db re-exports
      v1/
        __init__.py               # api_router aggregating all routers, mounted at /api/v1 (or root, see note below)
        auth.py
        customers.py
        invoices.py
        payments.py
        reminders.py
        tax_rates.py
        dashboard.py
        reports.py
        audit_log.py
        system.py                  # kill-switch endpoint
    tasks/
      __init__.py
      celery_app.py                # Celery() instance, broker/backend = Redis, beat schedule config
      reminder_dispatch.py          # periodic task: claim + send loop, catch-up logic
      email.py                      # send_reminder_email(), send_invoice_email(), send_admin_alert() — thin wrapper over provider (SES-class), swappable via interface for tests
  alembic/
    env.py
    script.py.mako
    versions/                      # see Section 3 for exact ordered file list
  tests/
    conftest.py                    # test DB (transactional rollback per test or dedicated test schema), fixtures: db_session, client, seeded users/customers, freeze_time helper
    unit/
      test_rounding.py
      test_validators_invoice.py
      test_validators_payment.py
      test_status_derivation.py
      test_reminder_scheduling_math.py
    integration/
      test_invoice_lifecycle.py
      test_customer_soft_delete.py
      test_reminder_dispatch_claim.py
      test_reminder_catchup.py
      test_reminder_retry_failure.py
      test_audit_log_immutability.py
      test_rbac.py
      test_reports.py
    e2e/
      playwright.config.py (or .ts if frontend added later — for v1 backend-only, this can be an API-level e2e using httpx against a live docker-compose stack; document as placeholder, do not block backend completion on it)
      test_full_flow.py
    factories.py                    # factory_boy factories for all models, used by both unit and integration tests
  seed/
    seed_dev.py                    # idempotent script: 5 customers, 10 invoices (mix of statuses), 5 payments, 1 admin user, reminder_rules, 1 tax_rate
```

Note on API prefix: `invoice-reminder-spec.md` Section 10 writes bare paths (`/customers`, `/invoices`, ...). Recommend mounting under `/api/v1` in `main.py` (`app.include_router(api_router, prefix="/api/v1")`) for forward-compatibility, while keeping router path operations bare (e.g. `@router.get("/customers")`) — document this prefix choice once in `main.py` and in the plan so the implementing agent doesn't silently deviate per-router.

---

## 2. DB Schema → SQLAlchemy Models

General conventions for every model:
- `id`: `UUID` primary key (`server_default=text("gen_random_uuid()")`, requires `pgcrypto` extension) — chosen over serial int PKs to avoid enumeration and to keep audit `entity_id` generically typed as UUID across all entity types.
- All monetary columns: `NUMERIC(12, 2)`.
- All FK columns: `NOT NULL` unless explicitly nullable per spec (audit `actor_id` is the one nullable FK).
- `created_at`/`updated_at`: `TIMESTAMPTZ`, `server_default=func.now()`, `updated_at` via `onupdate=func.now()`, via a shared `TimestampMixin` in `app/models/mixins.py`.
- All timestamps stored UTC (`TIMESTAMPTZ`), per design.md decision.

### `app/models/customer.py` — `Customer` / table `customers`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| name | String(255) | NOT NULL |
| email | String(255) | NOT NULL |
| phone | String(50) | NULL |
| billing_address | Text | NOT NULL |
| is_active | Boolean | NOT NULL, default True |
| created_at, updated_at | TIMESTAMPTZ | via mixin |

### `app/models/tax_rate.py` — `TaxRate` / table `tax_rates`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| name | String(100) | NOT NULL |
| rate_percent | NUMERIC(5,2) | NOT NULL, CHECK (rate_percent >= 0 AND rate_percent <= 100) |
| effective_from | Date | NOT NULL |
| effective_to | Date | NULL |
| is_active | Boolean | NOT NULL, default True |

Business invariant enforced in `services/tax_rates.py`, not DB constraint: at most one `is_active=True` row with `effective_to IS NULL` at a time (the "current global rate"). Implement via a single-row-boolean trick / service-layer enforcement using `SELECT ... FOR UPDATE` on the active row before flipping. Document this explicitly as a known service-layer (not DB-layer) invariant.

### `app/models/invoice.py` — `Invoice` / table `invoices`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| invoice_number | String(20) | UNIQUE, NULL (null while Draft) |
| customer_id | UUID FK -> customers.id | NOT NULL |
| status | Enum(`draft`,`issued`,`partially_paid`,`paid`,`cancelled`) | NOT NULL, default `draft` |
| issue_date | Date | NULL (set at Issue) |
| due_date | Date | NOT NULL |
| currency | String(3) | NOT NULL, default `INR`, CHECK (currency = 'INR') |
| subtotal | NUMERIC(12,2) | NOT NULL, default 0 |
| tax_amount | NUMERIC(12,2) | NOT NULL, default 0 |
| total_amount | NUMERIC(12,2) | NOT NULL, default 0 |
| amount_paid | NUMERIC(12,2) | NOT NULL, default 0, CHECK (amount_paid >= 0) |
| customer_name_snapshot | String(255) | NULL (set at Issue) |
| customer_email_snapshot | String(255) | NULL (set at Issue) |
| customer_address_snapshot | Text | NULL (set at Issue) |
| cancelled_at | TIMESTAMPTZ | NULL |
| cancellation_reason | Text | NULL |
| created_at, updated_at | TIMESTAMPTZ | via mixin |

Table-level CHECK: `amount_paid <= total_amount` (defense-in-depth alongside service-layer overpayment check). Index on `(customer_id)`, `(status)`, `(due_date)` for report queries.

### `app/models/invoice_line_item.py` — `InvoiceLineItem` / table `invoice_line_items`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| invoice_id | UUID FK -> invoices.id, ON DELETE CASCADE | NOT NULL |
| description | Text | NOT NULL |
| quantity | NUMERIC(10,2) | NOT NULL, CHECK (quantity > 0) |
| unit_price | NUMERIC(12,2) | NOT NULL, CHECK (unit_price >= 0) |
| tax_rate_snapshot | NUMERIC(5,2) | NULL (set at Issue) |
| line_subtotal | NUMERIC(12,2) | NOT NULL, default 0 |
| line_tax | NUMERIC(12,2) | NOT NULL, default 0 |
| line_total | NUMERIC(12,2) | NOT NULL, default 0 |

### `app/models/payment.py` — `Payment` / table `payments`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| invoice_id | UUID FK -> invoices.id | NOT NULL |
| amount | NUMERIC(12,2) | NOT NULL, CHECK (amount > 0) |
| payment_date | Date | NOT NULL |
| method | Enum(`cash`,`bank_transfer`,`upi`,`cheque`) | NOT NULL |
| notes | Text | NULL |
| recorded_by | UUID FK -> users.id | NOT NULL |
| created_at | TIMESTAMPTZ | via mixin (no updated_at — payments are immutable once created) |

### `app/models/reminder_rule.py` — `ReminderRule` / table `reminder_rules`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| code | String(50) | UNIQUE, NOT NULL (`before_due_3d`, `on_due`, `overdue_7d`, `overdue_14d`, `overdue_30d`) |
| offset_days | Integer | NOT NULL (negative = before due, e.g. -3, 0, 7, 14, 30) |
| template_id | String(100) | NOT NULL (references an email template key, no separate templates table in v1) |

Seeded once via migration (fixed 5 rows), not user-editable via API in v1.

### `app/models/reminder_instance.py` — `ReminderInstance` / table `reminder_instances`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| invoice_id | UUID FK -> invoices.id | NOT NULL |
| rule_id | UUID FK -> reminder_rules.id | NOT NULL |
| scheduled_for | TIMESTAMPTZ | NOT NULL |
| status | Enum(`scheduled`,`sent`,`cancelled`,`failed`) | NOT NULL, default `scheduled` |
| sent_at | TIMESTAMPTZ | NULL |
| cancelled_at | TIMESTAMPTZ | NULL |
| cancellation_reason | Text | NULL |
| attempt_count | Integer | NOT NULL, default 0 |

**`UNIQUE(invoice_id, rule_id)`** — table-level `UniqueConstraint`, this is the exactly-once dispatch guardrail. Index on `(status, scheduled_for)` for the dispatch query.

### `app/models/audit_log.py` — `AuditLogEntry` / table `audit_log`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| entity_type | String(50) | NOT NULL |
| entity_id | UUID | NOT NULL |
| action | String(100) | NOT NULL |
| actor_id | UUID FK -> users.id | **NULLABLE** (null = system) |
| before_state | JSONB | NULL |
| after_state | JSONB | NULL |
| timestamp | TIMESTAMPTZ | NOT NULL, server_default=func.now() |

No `updated_at`. Append-only enforced at the DB grant level (Section 3, migration) — model has no update/delete helper methods; `services/audit.py` only ever exposes `record(...)` which does an INSERT.

### `app/models/user.py` — `User` / table `users`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| name | String(255) | NOT NULL |
| email | String(255) | UNIQUE, NOT NULL |
| role | Enum(`admin`,`finance_staff`,`viewer`) | NOT NULL |
| password_hash | String(255) | NOT NULL |
| is_active | Boolean | NOT NULL, default True |

---

## 3. Alembic Migration Plan

Run `alembic init alembic` inside `backend/`, wire `env.py` to import `app.db.base.Base.metadata` and `app.config.settings.DATABASE_URL`. Migrations in strict order (each is its own file, generated via `alembic revision --autogenerate -m "..."` then hand-reviewed, since autogenerate won't produce partial indexes/grants):

1. `0001_enable_extensions` — `CREATE EXTENSION IF NOT EXISTS pgcrypto;` (for `gen_random_uuid()`).
2. `0002_create_users` — `users` table + `role` enum type.
3. `0003_create_customers` — `customers` table.
4. `0004_create_tax_rates` — `tax_rates` table.
5. `0005_create_invoices` — `invoices` table + `status` enum, FK to `customers`, CHECK constraints, indexes on `customer_id`/`status`/`due_date`.
6. `0006_create_invoice_line_items` — FK to `invoices` (CASCADE).
7. `0007_create_payments` — `method` enum, FKs to `invoices` and `users`.
8. `0008_create_reminder_rules` — table + seed data (data migration inserting the 5 fixed rows: `before_due_3d/-3`, `on_due/0`, `overdue_7d/7`, `overdue_14d/14`, `overdue_30d/30`).
9. `0009_create_reminder_instances` — `status` enum, FKs, **`UNIQUE(invoice_id, rule_id)`**, index on `(status, scheduled_for)`.
10. `0010_create_audit_log` — table, then raw SQL: `REVOKE UPDATE, DELETE ON audit_log FROM PUBLIC;` and explicitly `REVOKE UPDATE, DELETE ON audit_log FROM <app_db_role>;` (grant only `INSERT, SELECT`). Document that migrations themselves (run as a superuser/owner role) can still alter the table schema, but the application's runtime DB role cannot UPDATE/DELETE rows — this is the actual v1 enforcement mechanism referenced in tasks.md 7.2.
11. `0011_seed_default_tax_rate` — data migration inserting one active `tax_rates` row (name e.g. "Standard Flat Rate", pick a placeholder rate_percent like 18.00, effective_from = today, is_active=true) so invoices have a rate to snapshot in dev/test.
12. `0013_create_system_settings` — small `system_settings` table (`key TEXT PK, value JSONB, updated_at`) for the reminder kill-switch flag (see Section 5).

Skip a dedicated admin-user migration — password must be hashed and migrations shouldn't embed secrets; `seed/seed_dev.py` owns user seeding (see Section 9).

Validation checkpoint after this section: `alembic upgrade head` runs clean against a fresh Postgres; `alembic downgrade base && alembic upgrade head` round-trips cleanly (verifies down_revision chain and reversibility of each migration's `downgrade()`).

---

## 4. Pydantic Schemas (`app/schemas/`)

Pattern per resource: `XCreate` (request), `XUpdate` (request, all fields optional), `XRead` (response, includes `id`/timestamps), `XInDB` internal variant only if needed. Use `pydantic.ConfigDict(from_attributes=True)` for ORM mode.

- **`customer.py`**: `CustomerCreate(name, email, phone: str|None, billing_address)`, `CustomerUpdate` (all optional), `CustomerRead` (+ `id, is_active, created_at, updated_at`).
- **`invoice.py`**: `LineItemCreate(description, quantity: Decimal, unit_price: Decimal)`, `LineItemRead` (+ snapshot/computed fields), `InvoiceCreate(customer_id, due_date, line_items: list[LineItemCreate])`, `InvoiceUpdate(due_date: date|None, line_items: list[LineItemCreate]|None)`, `InvoiceRead` (all columns + `is_overdue: bool` computed property + nested `line_items: list[LineItemRead]`), `InvoiceIssueRequest` (empty body or optional note), `InvoiceCancelRequest(reason: str)`.
- **`payment.py`**: `PaymentCreate(amount: Decimal, payment_date: date, method: PaymentMethod, notes: str|None)`, `PaymentRead` (+ `id, recorded_by, created_at`), `PaymentCreateResponse` wrapping `PaymentRead` plus optional `duplicate_warning: bool` / `duplicate_of: UUID|None` for the confirm-then-record flow (see Section 6).
- **`reminder.py`**: `ReminderRuleRead(code, offset_days)`, `ReminderInstanceRead(id, rule_code, scheduled_for, status, sent_at, cancelled_at, cancellation_reason, attempt_count)`, `ReminderRescheduleRequest(new_scheduled_for: datetime)`, `ReminderCancelRequest(reason: str)`.
- **`tax_rate.py`**: `TaxRateCreate(name, rate_percent: Decimal, effective_from: date)`, `TaxRateRead`.
- **`audit.py`**: `AuditLogEntryRead(id, entity_type, entity_id, action, actor_id: UUID|None, before_state: dict|None, after_state: dict|None, timestamp)`.
- **`user.py`**: `UserRead(id, name, email, role, is_active)`, `LoginRequest(email, password)`, `LoginResponse(access_token, token_type, user: UserRead)`. No `/users` CRUD endpoint in v1 — users are seeded only (see note below).
- **`dashboard.py`**: `DashboardSummary(total_outstanding: Decimal, overdue_count: int, upcoming_due: list[InvoiceRead], recent_payments: list[PaymentRead])`.
- **`reports.py`**: `AgingBucket(range_label, invoices: list[InvoiceRead], total: Decimal)`, `AgingReport(buckets: list[AgingBucket])`, `CollectionsReportRow` / `CollectionsReport(period_start, period_end, payments: list[PaymentRead], total: Decimal)`, `CustomerStatement(customer: CustomerRead, invoices: list[InvoiceRead], payments: list[PaymentRead])`.
- **`common.py`**: `PaginatedResponse[T](items: list[T], total: int, page: int, page_size: int)`, `ErrorResponse(detail: str, code: str)`.

Note: user creation/management isn't explicitly listed in Section 10's API surface — spec only shows `/auth/login`/`/auth/logout`. Users are seeded only via `seed/seed_dev.py` / direct DB for v1, with no `/users` CRUD endpoint.

---

## 5. API Routers

All under `app/api/v1/`, mounted at `/api/v1`. Every state-changing route depends on `Depends(require_role(...))` from `app/core/permissions.py`; every route depends on `Depends(get_current_user)` except `/auth/login`.

- **`auth.py`**: `POST /auth/login` (public, calls `services/auth.py::authenticate`), `POST /auth/logout` (any authenticated role, invalidates session/token).
- **`customers.py`**: `GET /customers` (list, all roles), `POST /customers` (Admin/FinanceStaff), `GET /customers/{id}` (all roles), `PATCH /customers/{id}` (Admin/FinanceStaff), `DELETE /customers/{id}` (Admin/FinanceStaff — always resolves to soft-delete per business rule).
- **`invoices.py`**: `POST /invoices` (create Draft, Admin/FinanceStaff), `GET /invoices` (list w/ status/customer filters, all roles), `GET /invoices/{id}` (all roles), `PATCH /invoices/{id}` (edit, Admin/FinanceStaff), `POST /invoices/{id}/issue` (Admin/FinanceStaff), `POST /invoices/{id}/cancel` (Admin/FinanceStaff).
- **`payments.py`**: `POST /invoices/{id}/payments` (Admin/FinanceStaff; accepts `?confirm_duplicate=true` query param or body flag to bypass duplicate-warning on second submit), `GET /invoices/{id}/payments` (all roles).
- **`reminders.py`**: `GET /invoices/{id}/reminders` (all roles), `POST /invoices/{id}/reminders/{reminder_id}/cancel` (Admin only), `POST /invoices/{id}/reminders/{reminder_id}/reschedule` (Admin only).
- **`system.py`**: `POST /system/reminders/kill-switch` (Admin only; body `{enabled: bool}`; persists to the `system_settings` key-value table from migration `0013`).
- **`tax_rates.py`**: `GET /tax-rates` (all roles), `POST /tax-rates` (Admin only — creating a new rate deactivates the prior active one via service layer).
- **`dashboard.py`**: `GET /dashboard/summary` (all roles).
- **`reports.py`**: `GET /reports/aging`, `GET /reports/collections?start=&end=`, `GET /reports/customer/{id}` (all roles).
- **`audit_log.py`**: `GET /audit-log?entity_type=&entity_id=` (Admin only — audit trail is sensitive, not explicit in spec so default to the stricter option).

---

## 6. Business-Rule Validator Functions

All live in `app/services/`, called from the corresponding `app/api/v1/*.py` router (never inline validation in routers — keeps routers thin and validators unit-testable without HTTP).

| Rule (spec source) | Function | Module | Called from |
|---|---|---|---|
| Edit rejected once fully paid | `assert_not_paid_for_edit(invoice)` | `services/invoices.py` | `PATCH /invoices/{id}` |
| Edit rejected below `amount_paid` | `assert_total_not_below_paid(new_total, amount_paid)` | `services/invoices.py` | `PATCH /invoices/{id}` |
| Tax snapshot immutability | `snapshot_tax_and_totals(invoice, line_items, active_tax_rate)` | `services/invoices.py` | `POST /invoices/{id}/issue` |
| Sequential invoice numbering at Issue | `assign_invoice_number(session)` (uses a DB sequence `invoice_number_seq`, formats `INV-%04d`) | `services/invoices.py` | `POST /invoices/{id}/issue` |
| Status derivation incl. Overdue | `derive_status(invoice) -> InvoiceStatus`, `is_overdue(invoice, now=None) -> bool` | `services/invoices.py` | `InvoiceRead` serialization, reports, dashboard |
| Cancel blocked with payments | `assert_no_payments_for_cancel(invoice)` | `services/invoices.py` | `POST /invoices/{id}/cancel` |
| Customer hard-delete block | `assert_no_open_invoices(customer)` | `services/customers.py` | `DELETE /customers/{id}` |
| Overpayment rejection | `assert_no_overpayment(invoice, new_payment_amount)` | `services/payments.py` | `POST /invoices/{id}/payments` |
| Duplicate payment heuristic | `detect_duplicate_payment(invoice, amount, window_minutes=60) -> Payment|None` | `services/payments.py` | `POST /invoices/{id}/payments` |
| Payment status transition | `recompute_invoice_status_after_payment(invoice)` | `services/payments.py` | after payment insert, same transaction |
| Fixed-point rounding | `round_half_up(value: Decimal) -> Decimal` | `core/rounding.py` | totals calc, reports |
| Reminder scheduling math | `compute_schedule(due_date: date) -> list[tuple[rule_code, scheduled_for: datetime]]` | `services/reminders.py` | `POST /invoices/{id}/issue`, due-date edit path |
| Reminder recalculation on due-date edit | `recalculate_scheduled_reminders(invoice, new_due_date)` | `services/reminders.py` | `PATCH /invoices/{id}` when `due_date` changes |
| Reminder cancellation on paid/cancelled | `cancel_remaining_reminders(invoice, reason)` | `services/reminders.py` | payment-triggered status change, invoice cancel |
| Exactly-once claim | `claim_reminder_instance(session, instance_id) -> ReminderInstance|None` | `services/reminders.py` | `tasks/reminder_dispatch.py` |
| Kill-switch check | `is_kill_switch_enabled(session) -> bool` | `services/reminders.py` | `tasks/reminder_dispatch.py` |
| Audit write | `record_audit(session, entity_type, entity_id, action, actor_id, before, after)` | `services/audit.py` | every mutating service function above |
| 7-year retention | enforced by omission — no DELETE routes exist for invoices/payments/audit_log in v1 | N/A | N/A |

---

## 7. Celery Task Design

`app/tasks/celery_app.py`:
```python
celery_app = Celery("invoice_reminder", broker=settings.REDIS_URL, backend=settings.REDIS_URL)
celery_app.conf.beat_schedule = {
    "dispatch-reminders": {
        "task": "app.tasks.reminder_dispatch.dispatch_due_reminders",
        "schedule": crontab(minute="*/5"),
    }
}
celery_app.conf.task_acks_late = True
celery_app.conf.task_reject_on_worker_lost = True
```

`app/tasks/reminder_dispatch.py` — `dispatch_due_reminders` (periodic task, doubles as scheduler-recovery pass):

1. Check `services.reminders.is_kill_switch_enabled(session)` — if true, return immediately (no query issued).
2. Compute `now = now_utc()`, `catchup_floor = now - timedelta(hours=24)`.
3. Query candidate ids: `SELECT id FROM reminder_instances WHERE status='scheduled' AND scheduled_for <= now ORDER BY scheduled_for`.
4. For each candidate, in its own short transaction:
   - If `scheduled_for < catchup_floor`: **do not claim/send**; record audit `action="reminder_skipped_catchup_window"`, leave `status='scheduled'` untouched (superseded naturally by the next scheduled reminder), continue.
   - Else, claim via `UPDATE reminder_instances SET status='sending', attempt_count = attempt_count + 1 WHERE id=:id AND status='scheduled' RETURNING *` combined with `SELECT ... FOR UPDATE SKIP LOCKED` semantics so concurrent workers skip already-locked rows instantly. If claim returns None, continue.
   - Enqueue `send_single_reminder.delay(instance.id)`.

`send_single_reminder` — dedicated Celery task (`bind=True`, `autoretry_for=(EmailDeliveryError,)`, `retry_backoff=True`, `retry_backoff_max=600`, `max_retries=3`):
1. Re-fetch invoice with `SELECT ... FOR UPDATE` inside the same transaction (serializes against a concurrent payment/cancel).
2. If `invoice.status in (Paid, Cancelled)`: transition this instance to `cancelled`, reason = `invoice paid`/`invoice cancelled`, audit, commit, return.
3. Else call `send_reminder_email(instance, invoice)`. On success: `status='sent'`, `sent_at=now`, audit `reminder_sent`, commit.
4. On `EmailDeliveryError`: Celery's autoretry handles requeue with backoff. On final failure (`max_retries` exceeded): `status='failed'`, audit `reminder_failed_permanent`, call `services.reminders.raise_admin_alert(instance)`.

Kill-switch is only checked at the claim step in `dispatch_due_reminders`; an already-enqueued `send_single_reminder` task is allowed to complete (satisfies "no new dispatch after switch is on," not "abort in-flight sends").

---

## 8. Fixed-Point Decimal Handling Strategy

- Every monetary value uses Python `decimal.Decimal`, never `float`. Pydantic schemas type monetary fields as `Decimal`, serialized as strings in API responses (`json_encoders={Decimal: str}`) to avoid float round-trip in JS clients.
- DB: all monetary columns `NUMERIC(12,2)`; SQLAlchemy `Numeric(asdecimal=True)`.
- Rounding helper (`app/core/rounding.py`):
```python
from decimal import Decimal, ROUND_HALF_UP

TWO_PLACES = Decimal("0.01")

def round_half_up(value: Decimal) -> Decimal:
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
```
Every derived monetary value (line totals, tax, invoice totals, report aggregates) MUST go through `round_half_up`. `services/invoices.py`'s totals computation is the single place line/invoice totals get computed — reports read stored, already-rounded values, never recompute.
- Property-based test (`tests/unit/test_rounding.py`, `hypothesis`): randomized line items/tax rates, assert `sum(line.line_subtotal) == invoice.subtotal`, `subtotal + tax_amount == total_amount` exactly post-rounding, `amount_paid` never exceeds `total_amount` across randomized payment sequences.

---

## 9. Seed/Fixture Data Plan

`backend/seed/seed_dev.py` — idempotent (checks existing rows by natural key before inserting):

1. 1 admin (`admin@example.com`), 1 finance_staff, 1 viewer test user — password from `SEED_ADMIN_PASSWORD` env var, hashed via `core/security.py`.
2. 1 tax rate (skip if an active one already exists).
3. 5 customers, varied.
4. 10 invoices, mixed statuses (2 draft, 4 issued/overdue-mix, 2 partially_paid, 1 paid, 1 cancelled) — built via real `services.invoices.issue_invoice` / `services.reminders.compute_schedule` calls, not hand-inserted rows.
5. 5 payments recorded via `services.payments.record_payment` (real service call) against the partially_paid/paid invoices.

`tests/factories.py` (factory_boy) mirrors these shapes at test scale; both share underlying construction logic where possible.

Validation checkpoint: `python -m seed.seed_dev` runs clean against a freshly migrated DB; `GET /dashboard/summary` afterward returns non-zero `total_outstanding` and `overdue_count`.

---

## 10. Local Dev Environment

`backend/docker-compose.yml`: `postgres:16` (db `invoice_reminder`, healthcheck `pg_isready`) + `redis:7` (healthcheck `redis-cli ping`).

App/worker/beat run on host: `uvicorn app.main:app --reload`, `celery -A app.tasks.celery_app worker -l info`, `celery -A app.tasks.celery_app beat -l info`. Document all three in `backend/README.md`.

Browser E2E ("pinchtab"/Playwright): v1 has no bundled frontend yet, so `tests/e2e/` is a placeholder — true Playwright browser E2E only makes sense once a frontend exists. `tests/integration/` (httpx against the live API) is the effective end-to-end coverage for this pass.

---

## 11. Phased Build Order

Each phase ends with an explicit validation gate.

**Phase 0 — Project skeleton**: `pyproject.toml`, `app/config.py`, `app/main.py` (health check), `docker-compose.yml`, `.env.example`. Gate: `docker compose up -d` healthy; `GET /health` returns 200.

**Phase 1 — Models + Migrations**: all 9 SQLAlchemy models + Alembic migrations in order (Section 3), including audit-log grant revocation and reminder_rules seed. Gate: `alembic upgrade head` clean; `downgrade base && upgrade head` round-trips; audit_log grants verified; 5 reminder_rules rows exist.

**Phase 2 — Core utilities**: `core/rounding.py`, `core/timezone.py`, `core/security.py`, `core/exceptions.py`. Gate: `pytest tests/unit/test_rounding.py` passes incl. hypothesis property test.

**Phase 3 — Business-rule services**: `services/customers.py`, `services/tax_rates.py`, `services/invoices.py`, `services/payments.py`, `services/reminders.py`, `services/audit.py`, plus `tests/factories.py`. Gate: `pytest tests/unit/` passes for all Section 6 validators.

**Phase 4 — Auth + RBAC**: `services/auth.py`, `core/permissions.py`, `api/v1/auth.py`. Gate: `pytest tests/integration/test_rbac.py` passes.

**Phase 5 — API routers**: customers, invoices, payments, tax-rates. Gate: `pytest tests/integration/test_invoice_lifecycle.py` and `test_customer_soft_delete.py` pass end-to-end via `TestClient`.

**Phase 6 — Reminders API + Celery dispatch**: `api/v1/reminders.py`, `api/v1/system.py`, `tasks/celery_app.py`, `tasks/reminder_dispatch.py`, `tasks/email.py` (fake backend for tests). Gate: `test_reminder_dispatch_claim.py`, `test_reminder_catchup.py`, `test_reminder_retry_failure.py` pass; celery worker/beat start clean.

**Phase 7 — Audit log endpoint**: `api/v1/audit_log.py`. Gate: `test_audit_log_immutability.py` passes — raw SQL UPDATE/DELETE via app DB role is rejected by Postgres.

**Phase 8 — Dashboard + Reports**: `services/dashboard.py`, `services/reports.py`, `api/v1/dashboard.py`, `api/v1/reports.py`. Gate: `test_reports.py` passes.

**Phase 9 — Seed data + smoke pass**: `seed/seed_dev.py`. Gate: full suite green; seed script succeeds; manual smoke of login + dashboard.

**Phase 10 — Property-based & scheduler-resilience closeout**: remaining tasks.md 9.1-9.8 items (simulated-restart, concurrent-dispatch idempotency). Gate: entire tasks.md checklist complete, `pytest tests/` green end-to-end.

### Critical Files for Implementation
- backend/app/models/invoice.py
- backend/app/models/reminder_instance.py
- backend/app/services/reminders.py
- backend/app/tasks/reminder_dispatch.py
- backend/alembic/versions/0010_create_audit_log.py
- backend/app/core/rounding.py
- backend/app/services/invoices.py
