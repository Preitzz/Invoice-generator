# Invoice Generator with Payment Reminder Engine — Specification (v1 Draft)

**Status:** Draft for review — Section 14 (Open Questions) contains unresolved decisions that must be answered before this is implementation-ready.

**Locked foundational decisions (confirmed with stakeholder):**
| Decision | Choice |
|---|---|
| Tenancy | Single-tenant (one business) |
| Payment recording | Manual entry only (no gateway/webhook) |
| Reminder channel | Email only |
| Partial payments | Allowed (installment against one invoice) |
| Currency | INR only |
| Tax model | Simple flat rate (not GST) |
| Invoice immutability | Locked only when **fully** paid; editable pre-full-payment but cannot be edited below sum of payments already received |
| Escalation policy | Fixed schedule: before-due (−3d), on-due, +7d, +14d, +30d overdue |
| Invoice numbering | Sequential: `INV-0001`, `INV-0002`, ... never reused |
| AI scope (v1) | None — fully deterministic. AI deferred to v2 (see Section 7) |

---

## 1. Product Vision

**Target users**
- Small/mid business owner or finance staff issuing invoices to customers and tracking receivables
- Single internal team — no external customer-facing portal in v1 (customers only receive emailed invoices/reminders, they don't log in)

**Primary goals**
- Generate accurate invoices with correct, immutable tax at time of issuance
- Track payment status, including partial/installment payments, without spreadsheets
- Automatically send reminders on a fixed schedule, and guarantee they stop the instant an invoice is fully paid — never before, never after, never twice

**Business value**
- Reduced Days Sales Outstanding (DSO) through consistent, unmissable reminders
- Elimination of manual reminder-tracking labor and human error (forgetting, double-sending, sending after payment)
- Clean audit trail for financial review/statutory record-keeping

**Success metrics**
- 0 incidents of reminders sent after full payment
- 0 duplicate reminder sends
- 100% of invoices tax-calculated with correct, reproducible rounding
- Reduction in average DSO after adoption (baseline to be measured)
- 100% of financial state changes captured in audit log

---

## 2. Functional Requirements

### 2.1 Customer Management
- Create/view/update customer records (name, email, phone, billing address)
- Soft-delete only (`is_active = false`) — a customer with any invoice that is not `Cancelled` or `Paid` **cannot** be hard-deleted, and even after soft-delete, historical invoices/reminders remain fully intact and unaffected
- Invoices snapshot customer name/email/address at issuance time (denormalized copy), so later edits to a customer record never alter historical invoices

### 2.2 Invoice Creation
- Draft invoices support multiple line items (description, quantity, unit price, tax rate)
- System computes subtotal, tax, and total using fixed-point decimal arithmetic (never float)
- Invoice number assigned sequentially at creation (or at "Issue" — see Open Questions §14.10) and is permanent

### 2.3 Invoice Editing
- Editable while in `Draft` or `Issued`/`Partially Paid` (i.e., anytime before full payment)
- **Guardrail:** an edit that would reduce the invoice total below the sum of payments already recorded is rejected outright
- Every edit is versioned in the audit log with before/after state

### 2.4 Invoice Status Management
Status is mostly system-derived, not freely settable by users. Valid states:
`Draft → Issued → Partially Paid → Paid`, with `Cancelled` reachable from `Draft`/`Issued`/`Partially Paid` (only if `amount_paid = 0`), and `Overdue` as a **derived flag** (computed: `due_date < today AND status not in (Paid, Cancelled)`), not a manually-set state.

### 2.5 Tax Calculation
- Flat tax rate applied per line item (rate configurable — see Open Questions §14.5 on whether it's global or per-item/customer)
- Tax is **snapshotted onto the invoice/line item at issuance** — later changes to the global tax rate never retroactively change an already-issued invoice

### 2.6 Payment Recording
- Manual entry by staff: amount, date, method (cash/bank transfer/UPI/cheque), notes
- System validates `amount_paid + new_payment <= total_amount` (see Open Questions §14.1 on overpayment handling)
- Duplicate-entry protection: warn/block if an identical amount is recorded for the same invoice within a short time window (heuristic, since there's no gateway idempotency key to rely on)

### 2.7 Reminder Scheduling
- On invoice issuance, the system schedules reminder instances per the fixed policy: −3 days, on due date, +7, +14, +30 days overdue
- Reminders are **recalculated** if due date changes via an edit (unsent ones rescheduled; sent ones remain historical)

### 2.8 Reminder Cancellation
- All scheduled (not-yet-sent) reminders for an invoice are cancelled the instant the invoice becomes `Paid` or `Cancelled`
- Cancellation is itself an audited event (reason: "invoice paid" / "invoice cancelled" / "manual override")

### 2.9 Overdue Escalation
- Fully automatic per the fixed schedule — no manual trigger required
- Admin can manually cancel or reschedule an individual reminder (human override), always logged

### 2.10 Dashboard
- Outstanding balance overview, count of overdue invoices, upcoming due invoices, recently received payments

### 2.11 Reports
- Aging report (0–30 / 31–60 / 61–90 / 90+ days overdue)
- Collections report (payments received in period)
- Per-customer statement
- (See Open Question §14.7 — confirm exact report list needed)

---

## 3. Non-Functional Requirements

| Category | Requirement |
|---|---|
| **Reliability** | All background operations (reminder dispatch, status transitions) are idempotent and safe to retry |
| **Scalability** | Single-tenant scale target (thousands of invoices/customers, not millions) — design should not preclude future growth, but no premature sharding/multi-tenant complexity |
| **Availability** | Business-hours criticality; reminder scheduler should target >99% uptime with alerting on missed runs |
| **Security** | Role-based access (Admin / Finance Staff / Viewer); passwords hashed (bcrypt/argon2); TLS in transit; encryption at rest |
| **Performance** | Dashboard/report queries <2s at expected scale; invoice creation <1s |
| **Auditability** | Every state-changing action (create, edit, payment, cancel, reminder sent/cancelled, manual override) recorded in an append-only audit log with actor, timestamp, before/after state — including automated/system actions |

---

## 4. Domain Model

### Entities

**Customer**
`id, name, email, phone, billing_address, is_active, created_at, updated_at`

**Invoice**
`id, invoice_number (unique, sequential), customer_id (FK), status, issue_date, due_date, currency (fixed: INR), subtotal, tax_amount, total_amount, amount_paid, customer_name_snapshot, customer_email_snapshot, customer_address_snapshot, cancelled_at, cancellation_reason, created_at, updated_at`

**InvoiceLineItem**
`id, invoice_id (FK), description, quantity, unit_price, tax_rate_snapshot, line_subtotal, line_tax, line_total`

**TaxRate**
`id, name, rate_percent, effective_from, effective_to, is_active`

**Payment**
`id, invoice_id (FK), amount, payment_date, method, notes, recorded_by (FK User), created_at`

**ReminderRule** (system config, not per-invoice)
`id, code (e.g. "before_due_3d", "on_due", "overdue_7d", "overdue_14d", "overdue_30d"), offset_days, template_id`

**ReminderInstance**
`id, invoice_id (FK), rule_id (FK), scheduled_for (datetime), status (scheduled/sent/cancelled/failed), sent_at, cancelled_at, cancellation_reason, attempt_count`

**AuditLogEntry**
`id, entity_type, entity_id, action, actor_id (nullable = system), before_state (JSON), after_state (JSON), timestamp`

**User**
`id, name, email, role (Admin/FinanceStaff/Viewer), password_hash, is_active`

### Lifecycle: Invoice
```
Draft → Issued → Partially Paid → Paid
   ↓        ↓            ↓
   └──── Cancelled (only if amount_paid = 0) ──┘
(Overdue is a derived flag, not a distinct stored transition)
```

### Lifecycle: ReminderInstance
```
Scheduled → Sent
Scheduled → Cancelled (invoice paid / cancelled / manual override)
Scheduled → Failed → (retry per policy) → Sent | Failed(permanent)
```

---

## 5. Business Rules

1. An invoice cannot be edited once fully paid.
2. An invoice can be edited before full payment, but its total can never be reduced below the sum of payments already recorded against it.
3. Tax is snapshotted at issuance and is immutable thereafter, regardless of later changes to the global tax rate configuration.
4. All reminders for an invoice are cancelled immediately upon full payment or cancellation — no reminder may be sent afterward.
5. Every reminder is sent **exactly once** — enforced via an atomic "claim before send" pattern at the database level (unique constraint on invoice+rule, status transition guarded by row lock).
6. Overdue escalation runs automatically on the fixed schedule; it requires no manual trigger, but an Admin may cancel or reschedule any individual reminder (logged).
7. An invoice can be cancelled only if `amount_paid = 0`. Cancelling an invoice with recorded payments is blocked in v1 (see Open Question §14.2 — refund/credit-note flow).
8. A customer cannot be hard-deleted while they have any invoice that is not `Paid` or `Cancelled`; deletion is always soft (`is_active = false`).
9. Invoice numbers are sequential and never reused, even when the invoice is later cancelled (numbering gaps from cancellations are expected and acceptable for audit purposes).
10. A payment cannot be recorded if it would make `amount_paid` exceed `total_amount` (pending final confirmation on overpayment handling — §14.1).
11. All monetary values use fixed-point decimal arithmetic (2 decimal places, round-half-up), never floating point.
12. Every state-changing action is captured in the audit log, including system/automated actions (actor = "system").

---

## 6. Edge Cases

| Edge Case | Handling |
|---|---|
| Partial payment | Moves status to `Partially Paid`; reminders continue on schedule until fully paid |
| Duplicate manual payment entry | Heuristic duplicate-detection (same invoice + same amount + short time window) surfaces a warning before allowing a second entry |
| Timezone | Single business timezone assumed (Asia/Kolkata, IST) for all due-date and reminder-scheduling logic, regardless of server host timezone |
| Retry after server restart | Reminder schedule is derived from durable DB state, never in-memory; on restart, the scheduler re-evaluates all `scheduled` reminders due now or in the past (see §14.3 for late-send vs skip policy) |
| Scheduler failure | Celery beat + heartbeat monitoring; alert if the periodic check hasn't run within expected window; task itself is idempotent so re-running after a crash cannot double-send |
| Reminder dispatch racing a payment update | Invoice status is re-verified transactionally immediately before the email is actually sent, not just at scheduling time |
| Invalid tax rate | Rejected at input validation (no negative rates, sane upper bound) |
| Deleted (soft-deleted) customer | Existing invoices/reminders are unaffected; reminder emails use the invoice's snapshotted customer email, not a live lookup |
| Cancelled invoice | Any already-scheduled reminders are cancelled (not deleted) with a reason, preserving audit history |
| Invoice edited after due-date change | Any unsent scheduled reminders are recalculated against the new due date; already-sent reminders remain historical record |
| Overpayment attempt | Currently rejected at validation — pending confirmation (§14.1) |
| Email bounce/delivery failure | Reminder marked `Failed`; retry policy pending confirmation (§14.4) |

---

## 7. AI Opportunities (Deferred to v2)

v1 is intentionally fully deterministic, per your decision, because reminder delivery and financial correctness are the core value proposition and must be trustworthy before layering AI on top. Documented here so the "AI-native" framing has a clear, responsible roadmap:

| Feature | Type | Guardrail principle |
|---|---|---|
| Invoice line-item description generation | Generative (assistive) | AI only drafts text; a human must review/approve before it's saved — never auto-populates financial fields |
| Payment delay prediction / customer risk scoring | Predictive | Advisory only, shown on dashboard; never blocks or allows any workflow action |
| Reminder tone/wording generation | Generative | AI only varies the copy inside a reminder; the deterministic scheduler still owns *whether* and *when* to send — AI never touches timing or delivery logic |
| Anomaly detection (unusual invoice/payment patterns) | Predictive/detection | Flags for human review only; never auto-blocks a transaction |
| Smart reminder timing | Predictive | Highest-risk item to combine with correctness guarantees — recommend the deterministic schedule always remains the source of truth, with AI only *suggesting* adjustments for human approval, never silently overriding the fixed policy |

**Core principle for all future AI features:** AI is never in the critical path of financial correctness or exactly-once delivery guarantees. It is always advisory, generative, or requires human approval — the deterministic engine remains authoritative.

---

## 8. Guardrails

- **Exactly-once reminder delivery:** DB-level uniqueness on `(invoice_id, rule_id)` for reminder instances; dispatch uses an atomic "claim" (`UPDATE ... WHERE status='scheduled' RETURNING`) so only one worker can ever send a given instance.
- **Payment verification before reminder:** invoice status is re-checked inside the same transaction as dispatch, immediately before sending.
- **Audit logging:** append-only table; no updates or deletes permitted on audit records, ever.
- **No duplicate invoices:** unique sequential invoice number constraint; duplicate-content heuristic warns staff (not a hard block, since legitimate repeat invoices happen).
- **Financial calculation correctness:** fixed-point decimal only, with a single documented rounding rule, verified by property-based tests.
- **Retry safety:** every background job re-derives its work from DB state rather than in-memory state, so re-running after a crash is always safe.
- **Human override:** Admins can manually cancel/reschedule a reminder or force a status correction — always logged with a reason, never silent.
- **Emergency reminder shutdown:** a single global kill-switch flag checked immediately before every dispatch, allowing all outgoing reminders to be halted instantly without a code deploy.

---

## 9. Evaluation Plan

- **Unit tests:** tax computation and rounding correctness across boundary amounts; business-rule validators (edit-below-payments rejection, overpayment rejection, cancellation-with-payment rejection).
- **Integration tests:** full invoice lifecycle (draft → issue → partial payment → full payment → reminders auto-cancelled); customer soft-delete leaving historical invoices untouched.
- **Scheduler tests:** simulated server restart mid-cycle — assert no duplicate sends and no silently-lost reminders beyond the agreed catch-up policy; simulated clock skew.
- **Idempotency tests:** fire the "send reminder" task twice concurrently for the same instance — assert exactly one email is sent (proven via the DB claim mechanism, not just application-level checks).
- **Financial accuracy tests:** property-based tests asserting `sum(line items) + tax == invoice total` across randomized inputs; `amount_paid` never exceeds `total_amount`; consistent rounding across many invoices.
- **AI evaluation metrics:** N/A for v1. When v2 AI features land: track hallucination/error rate on generated content, human-override rate, prediction precision/recall for risk scoring, and confirm guardrail-violation rate stays at 0.

---

## 10. API Design (REST)

```
Auth
POST   /auth/login
POST   /auth/logout

Customers
GET    /customers
POST   /customers
GET    /customers/{id}
PATCH  /customers/{id}
DELETE /customers/{id}          # soft-delete only

Invoices
POST   /invoices                # create draft
GET    /invoices
GET    /invoices/{id}
PATCH  /invoices/{id}           # edit (blocked per business rules)
POST   /invoices/{id}/issue
POST   /invoices/{id}/cancel

Payments
POST   /invoices/{id}/payments
GET    /invoices/{id}/payments

Reminders
GET    /invoices/{id}/reminders
POST   /invoices/{id}/reminders/{reminder_id}/cancel
POST   /invoices/{id}/reminders/{reminder_id}/reschedule
POST   /system/reminders/kill-switch     # emergency shutdown, Admin only

Tax Rates
GET    /tax-rates
POST   /tax-rates

Dashboard
GET    /dashboard/summary

Reports
GET    /reports/aging
GET    /reports/collections
GET    /reports/customer/{id}

Audit
GET    /audit-log?entity_type=&entity_id=
```

---

## 11. Database Design (normalized, PostgreSQL)

```
customers(id PK, name, email, phone, billing_address, is_active, created_at, updated_at)

tax_rates(id PK, name, rate_percent, effective_from, effective_to, is_active)

invoices(
  id PK, invoice_number UNIQUE, customer_id FK -> customers,
  status, issue_date, due_date, currency,
  subtotal, tax_amount, total_amount, amount_paid,
  customer_name_snapshot, customer_email_snapshot, customer_address_snapshot,
  cancelled_at, cancellation_reason, created_at, updated_at
)

invoice_line_items(
  id PK, invoice_id FK -> invoices,
  description, quantity, unit_price,
  tax_rate_snapshot, line_subtotal, line_tax, line_total
)

payments(
  id PK, invoice_id FK -> invoices,
  amount, payment_date, method, notes,
  recorded_by FK -> users, created_at
)

reminder_rules(id PK, code UNIQUE, offset_days, template_id)

reminder_instances(
  id PK, invoice_id FK -> invoices, rule_id FK -> reminder_rules,
  scheduled_for, status, sent_at, cancelled_at, cancellation_reason, attempt_count,
  UNIQUE(invoice_id, rule_id)
)

users(id PK, name, email UNIQUE, role, password_hash, is_active)

audit_log(
  id PK, entity_type, entity_id, action, actor_id NULLABLE,
  before_state JSONB, after_state JSONB, timestamp,
  -- append-only: no UPDATE/DELETE grants on this table
)
```

---

## 12. Event Flow

1. **Invoice Creation** — Staff creates a Draft invoice with line items; system computes subtotal/tax/total using the currently-active flat tax rate; invoice_number is reserved.
2. **Invoice Delivery** — Staff issues the invoice (`Draft → Issued`); tax and totals are snapshotted permanently; the system schedules all five ReminderInstances (−3d, on-due, +7, +14, +30) based on the due date; invoice is emailed to the customer's snapshotted address.
3. **Payment** — Staff records a payment; system validates it doesn't exceed the outstanding balance and doesn't reduce effective total below what's owed; status becomes `Partially Paid` or `Paid`.
4. **Reminder Scheduling** — Already covered at issuance; if due date is edited pre-full-payment, unsent ReminderInstances are recalculated.
5. **Reminder Execution** — A periodic Celery task queries `reminder_instances` where `scheduled_for <= now AND status='scheduled'`, atomically claims each row, re-verifies the invoice is not fully paid/cancelled inside the same transaction, then sends the email and marks `Sent`.
6. **Payment Confirmation** — The moment a payment brings `amount_paid == total_amount`, status flips to `Paid` and all remaining `scheduled` ReminderInstances for that invoice are immediately cancelled.
7. **Reminder Cancellation** — Triggered by full payment, invoice cancellation, or manual Admin override; always logged with a reason; cancelled instances are retained (not deleted) for audit history.

---

## 13. Architecture

```
┌─────────────────────┐     ┌───────────────────────┐     ┌────────────────┐
│ React + TypeScript   │───▶│ FastAPI (Python)      │───▶│ PostgreSQL     │
│ (staff-facing UI)     │◀───│ REST API + business   │◀───│ (source of     │
└─────────────────────┘     │ rule validation        │     │  truth)        │
                             └──────────┬────────────┘     └────────────────┘
                                        │
                              ┌─────────▼──────────┐
                              │ Celery worker(s)    │
                              │ - reminder dispatch │
                              │ - status recompute  │
                              └─────────┬───────────┘
                              ┌─────────▼──────────┐
                              │ Redis (broker +     │
                              │ Celery beat schedule)│
                              └─────────┬───────────┘
                              ┌─────────▼──────────┐
                              │ Email provider      │
                              │ (e.g. AWS SES)       │
                              └─────────────────────┘
```

**Cloud:** given single-tenant, modest scale — a minimal AWS footprint is appropriate: ECS Fargate (or a single EC2) for API + worker, RDS Postgres (with automated backups + encryption at rest), ElastiCache Redis for Celery broker, SES for outbound email, CloudWatch for scheduler heartbeat alerting.

**Reliability notes:**
- Celery tasks configured with bounded retry + exponential backoff, dead-letter alerting on permanent failure
- Celery beat schedule itself is stateless/re-derivable — the *source of truth* for "what's due" is always the `reminder_instances` table, never beat's own memory
- All timestamps stored in UTC; business logic (due-date comparisons) explicitly converts to Asia/Kolkata for evaluation

---

## 14. Open Questions (must be resolved before implementation)

1. **Overpayment:** if a customer accidentally pays more than the outstanding balance, should the system (a) reject the payment outright, (b) allow it and track a credit balance, or (c) allow it with a warning but no credit tracking?
2. **Cancellation with existing payments:** v1 currently blocks cancelling an invoice once any payment exists. Is a refund/credit-note flow actually needed for v1, or is "block until reversed manually outside the system" acceptable?
3. **Missed-reminder catch-up policy:** if the scheduler was down and missed a reminder's exact window, should it be sent late (bounded catch-up window, e.g. within 24h) once the scheduler recovers, or skipped in favor of the next scheduled reminder?
4. **Email failure/bounce handling:** how many automatic retries before a reminder is marked permanently failed, and should that trigger an alert to an Admin for manual follow-up?
5. **Tax rate scope:** is there a single global flat tax rate, or does it vary per line item / per customer / per product category?
6. **Authentication:** is simple internal username/password sufficient, or is SSO/MFA required given this handles financial data?
7. **Reports:** confirm the exact report list — is Aging + Collections + Customer Statement sufficient, or is a Tax Summary report also needed?
8. **Data retention:** how long must invoices, payments, and audit logs be retained? (Indian financial record-keeping norms are typically 6–8 years even outside GST — please confirm the applicable requirement for your business.)
9. **Rounding rule:** confirming round-half-up to 2 decimal places (nearest paisa) as the standard — acceptable?
10. **Due date precision:** is "due" simply end-of-day IST on the due date, or is a specific cutoff time needed?
11. **Invoice numbering timing:** is the invoice number assigned at Draft creation, or only when the invoice is Issued (drafts never sent might otherwise create numbering gaps)?

---

*This document is a draft. Sections 10–13 (API/DB/Architecture) may need revision once Section 14's answers are locked — particularly #1, #2, and #5, which touch the domain model directly.*
