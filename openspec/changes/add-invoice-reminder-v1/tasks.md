## 1. Foundation

- [ ] 1.1 Stand up PostgreSQL schema (customers, tax_rates, invoices, invoice_line_items, payments, reminder_rules, reminder_instances, users, audit_log) per `invoice-reminder-spec.md` Section 11
- [ ] 1.2 Set up API project skeleton with RBAC middleware scaffolding (Admin / Finance Staff / Viewer)
- [ ] 1.3 Set up background worker project skeleton with Redis broker connection
- [ ] 1.4 Configure fixed-point decimal handling (DB `NUMERIC`, language-level Decimal) and a shared round-half-up rounding utility

## 2. User Access Control

- [ ] 2.1 Implement user model with bcrypt/argon2 password hashing
- [ ] 2.2 Implement `/auth/login` and `/auth/logout`
- [ ] 2.3 Implement RBAC enforcement on all state-changing endpoints; Viewer read-only

## 3. Customer Management

- [ ] 3.1 Implement customer create/view/update endpoints
- [ ] 3.2 Implement soft-delete-only deletion, blocking hard-delete while non-Paid/Cancelled invoices exist
- [ ] 3.3 Implement customer-data snapshotting onto invoices at issuance

## 4. Invoice Management

- [ ] 4.1 Implement Draft invoice creation with line items (no invoice number assigned)
- [ ] 4.2 Implement subtotal/tax/total computation using global flat tax rate and round-half-up rounding
- [ ] 4.3 Implement Issue transition: assign sequential invoice number, snapshot tax/totals, transition to `Issued`
- [ ] 4.4 Implement invoice editing with the "cannot reduce total below amount_paid" guardrail and audit logging of before/after state
- [ ] 4.5 Implement derived `Overdue` computation using end-of-day IST (23:59:59 Asia/Kolkata) on due date
- [ ] 4.6 Implement cancellation, blocked when `amount_paid > 0`

## 5. Payment Recording

- [ ] 5.1 Implement manual payment entry endpoint (amount, date, method, notes, recorded_by)
- [ ] 5.2 Implement overpayment rejection validation (`amount_paid + new_payment <= total_amount`)
- [ ] 5.3 Implement duplicate-payment heuristic warning (same amount, short time window)
- [ ] 5.4 Implement status transition to `Partially Paid` / `Paid` driven by recorded payments

## 6. Reminder Scheduling & Dispatch

- [ ] 6.1 Implement fixed 5-instance reminder scheduling on invoice issuance (-3d, on-due, +7d, +14d, +30d)
- [ ] 6.2 Implement reminder recalculation on due-date edits (unsent only)
- [ ] 6.3 Implement atomic claim-before-send dispatch with unique `(invoice_id, rule_id)` constraint
- [ ] 6.4 Implement in-transaction invoice-status re-verification immediately before send
- [ ] 6.5 Implement automatic reminder cancellation on full payment / invoice cancellation, with audit reason
- [ ] 6.6 Implement Admin manual cancel/reschedule of an individual reminder instance
- [ ] 6.7 Implement bounded 24-hour catch-up on scheduler recovery; skip anything older
- [ ] 6.8 Implement 3-retry-with-backoff email delivery, permanent `Failed` status, and Admin alert on exhaustion
- [ ] 6.9 Implement global emergency reminder kill-switch checked before every dispatch

## 7. Audit Logging

- [ ] 7.1 Implement append-only audit_log writes for every state-changing action (manual and system actor)
- [ ] 7.2 Enforce no UPDATE/DELETE grants on the audit_log table
- [x] 7.3 Implement 7-year retention guard preventing deletion of invoices/payments/audit entries before retention expiry — enforced via DB grant revocation (REVOKE DELETE FROM app_user) on `invoices` and `payments`, matching the existing `audit_log` enforcement (0010_create_audit_log.py). See `backend/alembic/versions/0014_revoke_delete_invoices_payments.py` and `backend/tests/integration/test_financial_records_no_hard_delete.py`. `invoice_line_items` DELETE is intentionally left grantable — it is not named in the spec's retention requirement, and `update_invoice` legitimately deletes/recreates a draft invoice's line items in place when edited.

## 8. Reporting & Dashboard

- [ ] 8.1 Implement `/dashboard/summary` (outstanding balance, overdue count, upcoming due, recent payments)
- [ ] 8.2 Implement Aging report (0-30 / 31-60 / 61-90 / 90+ buckets)
- [ ] 8.3 Implement Collections report (payments received in a period)
- [ ] 8.4 Implement Customer Statement report

## 9. Testing & Evaluation

- [ ] 9.1 Unit tests: tax computation and rounding correctness across boundary amounts
- [ ] 9.2 Unit tests: business-rule validators (edit-below-payments rejection, overpayment rejection, cancellation-with-payment rejection)
- [ ] 9.3 Integration test: full invoice lifecycle (draft -> issue -> partial payment -> full payment -> reminders auto-cancelled)
- [ ] 9.4 Integration test: customer soft-delete leaves historical invoices untouched
- [ ] 9.5 Scheduler test: simulated restart mid-cycle — no duplicate sends, catch-up window honored, older-than-24h skipped
- [ ] 9.6 Idempotency test: concurrent dispatch of the same reminder instance sends exactly one email
- [ ] 9.7 Property-based test: `sum(line items) + tax == total` across randomized inputs; `amount_paid` never exceeds `total_amount`
- [ ] 9.8 Test: email failure retries 3 times then marks Failed and alerts Admin
