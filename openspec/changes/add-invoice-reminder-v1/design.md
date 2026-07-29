## Context

This is a greenfield build — there is no existing implementation. `invoice-reminder-spec.md` in the repo root already contains a detailed narrative design (Sections 10-13: API, DB schema, event flow, architecture) that this change's specs are derived from. See `proposal.md` - Why for motivation. This document records the design-level decisions needed to go from those specs to an implementation plan, and reproduces (rather than duplicates verbatim) the key architectural choices from the source draft, now updated for the locked answers to all 11 open questions.

## Goals / Non-Goals

**Goals:**
- Implement the seven capability specs (`customer-management`, `invoice-management`, `payment-recording`, `reminder-scheduling-dispatch`, `audit-logging`, `reporting-dashboard`, `user-access-control`) as a single deployable v1 system.
- Preserve the source draft's core guardrails: exactly-once reminder delivery, fixed-point monetary math, append-only audit log.
- Bake all 11 previously-open decisions into the implementation as hard constraints, not configurable toggles (a future version can revisit them deliberately).

**Non-Goals:**
- No multi-tenant support, no payment gateway integration, no SMS/WhatsApp reminder channels, no refund/credit-note flow, no AI features (see `invoice-reminder-spec.md` Section 7 — deferred to v2).
- No GST-style multi-rate tax engine — single global flat rate only.
- No SSO/MFA.

## Decisions

- **Backend/worker split (API + Celery-style worker + Postgres + Redis)**: Adopt the architecture from `invoice-reminder-spec.md` Section 13 (React/TS frontend, FastAPI-style REST API, PostgreSQL as source of truth, background worker for reminder dispatch, Redis as broker, SES-class provider for email). Rationale: reminder dispatch must run independently of API request/response cycles and be safely retryable; a durable-queue background worker is the standard pattern for that. Alternative considered: cron-only dispatch without a queue — rejected because it doesn't give per-task retry/backoff semantics needed for the email-failure-retry requirement.
- **Reminder dispatch correctness via DB-level claim, not application-level locking**: Use a unique `(invoice_id, rule_id)` constraint plus an atomic `UPDATE ... WHERE status='scheduled' RETURNING` claim, re-verifying invoice status inside the same transaction immediately before send. Rationale: this is the only pattern that survives concurrent workers and process crashes without double-sending or losing exactly-once guarantees; in-memory locks or application-level check-then-act are not crash-safe. Alternative considered: idempotency keys on the email provider side alone — rejected as a sole mechanism because it doesn't prevent duplicate claim/processing work, only duplicate delivery.
- **All monetary values as fixed-point decimals (e.g. DB `NUMERIC`/`DECIMAL`, language-level Decimal type), never float**: Required for the round-half-up-to-paisa rounding decision to be reproducible and testable via property-based tests.
- **Invoice number reservation deferred to Issue transition**: Implemented as a DB sequence (or equivalent) incremented only inside the `issue` operation's transaction, never touched by `create draft`.
- **Timezone handling**: All timestamps stored in UTC; due-date/overdue comparisons and reminder `scheduled_for` computation explicitly convert to `Asia/Kolkata` at evaluation time, per the due-date-precision decision (23:59:59 IST on the due date).
- **Retry/backoff for reminder email failures**: 3 attempts with exponential backoff (worker-level retry policy), final failure flips the reminder instance to permanently `Failed` and enqueues an Admin-facing alert (e.g. in-app notification and/or email to Admins) — not a silent failure.
- **Missed-reminder catch-up implemented as a scheduler-recovery pass**: On worker startup (or on each periodic tick), the dispatcher queries `scheduled` instances with `scheduled_for <= now`; those within the last 24 hours are dispatched (subject to normal claim + re-verification), those older are transitioned to a "skipped (missed catch-up window)" audit event but left for the next naturally scheduled instance to supersede them functionally (no separate stored state needed beyond the audit trail, since the fixed 5-instance schedule per invoice means "skip" just means "don't send this one, the next one will still fire on its own schedule").
- **RBAC enforcement**: Role check (Admin / Finance Staff / Viewer) enforced at the API layer on every state-changing endpoint; Viewer is read-only across the board.

## Risks / Trade-offs

- [Risk] Bounded 24h catch-up could still send a reminder that reads as "late" to the customer (e.g. an on-due-date notice arriving 20 hours late) → Mitigation: reminder templates should be worded in a way that remains accurate regardless of small delivery delay (avoid "today is your due date" phrasing tied to exact send time); acceptable trade-off given the alternative (silently dropping reminders) is worse for collections.
- [Risk] Global flat tax rate cannot represent customers/products that legitimately need a different rate → Mitigation: explicitly deferred, documented as a v2 candidate if the business's tax needs grow; not a silent gap, it's a locked v1 decision.
- [Risk] No refund/credit-note flow means payment-entry mistakes on a since-cancelled-attempt invoice require manual, out-of-band correction → Mitigation: audit log captures the full before/after trail so manual corrections remain traceable even without an in-app reversal flow.
- [Risk] Simple username/password auth is weaker than SSO/MFA for a system handling financial data → Mitigation: bcrypt/argon2 hashing, TLS in transit, encryption at rest, and RBAC limit blast radius; explicitly flagged as a v1 trade-off to revisit if compliance requirements change.

## Migration Plan

Not applicable in the traditional sense — this is the initial build, so there is no prior system state to migrate from. Deployment sequencing: (1) stand up Postgres schema per `invoice-reminder-spec.md` Section 11, (2) deploy API, (3) deploy worker + Redis broker with the kill-switch defaulted to "off" (reminders disabled) until the on-call team confirms the schedule and dispatch logic in a staging pass, (4) enable the kill-switch to "on" (reminders enabled) for production traffic. Rollback: the kill-switch itself doubles as the primary rollback lever for reminder dispatch without a redeploy; a full rollback of the release is a standard redeploy of the previous version given there is no prior production data to reconcile.
