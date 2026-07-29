## Why

The business currently tracks invoices and payment follow-up manually (spreadsheets, memory), which causes missed or duplicate reminders, inconsistent tax rounding, and no audit trail for financial state changes. `invoice-reminder-spec.md` (v1 draft) defines a deterministic, single-tenant Invoice Generator with a fixed-schedule email Payment-Reminder Engine to replace this. That draft left 11 open questions (Section 14) blocking implementation; this change locks all 11 with concrete decisions (documented inline in each spec as a "Decision" note) and turns the draft into OpenSpec capability specs ready to build against.

## What Changes

- Introduce seven new capabilities covering the full v1 system: customer management, invoice management, payment recording, reminder scheduling & dispatch, audit logging, reporting/dashboard, and user access control.
- Resolve all 11 Section-14 open questions with concrete, documented defaults:
  - Overpayment is rejected outright (no credit-balance tracking in v1).
  - Cancellation of an invoice with recorded payments is blocked in v1 (no refund/credit-note flow; reversed manually outside the system).
  - Missed reminders get a bounded 24-hour catch-up window after scheduler recovery, then are skipped in favor of the next scheduled reminder.
  - Reminder email failures get 3 automatic retries with backoff, then are marked permanently `Failed` and raise an Admin alert.
  - Tax rate is a single global flat rate (not per-item/customer/product).
  - Authentication is simple internal username/password (bcrypt/argon2 hashed); no SSO/MFA in v1.
  - Reports are limited to Aging, Collections, and Customer Statement (no Tax Summary in v1).
  - Data retention is 7 years for invoices, payments, and audit logs (Indian financial record-keeping norm).
  - Rounding is round-half-up to 2 decimal places (nearest paisa).
  - Due date precision is end-of-day IST (23:59:59 Asia/Kolkata) on the due date.
  - Invoice numbers are assigned at "Issue" time (not at Draft creation), so abandoned drafts never create numbering gaps.
- No breaking changes — this is the initial buildout of the system (no prior specs exist).

## Capabilities

### New Capabilities
- `customer-management`: Customer CRUD, soft-delete-only lifecycle, and denormalized snapshotting of customer data onto invoices at issuance.
- `invoice-management`: Draft/Issue/edit lifecycle, line items, tax computation and snapshotting, status derivation (including derived `Overdue`), invoice numbering, and cancellation rules.
- `payment-recording`: Manual payment entry, overpayment rejection, duplicate-entry detection, and status transitions (`Partially Paid` / `Paid`) driven by recorded payments.
- `reminder-scheduling-dispatch`: Fixed-schedule reminder generation on issuance, recalculation on due-date edits, exactly-once dispatch, cancellation on payment/cancellation, missed-reminder catch-up policy, and email failure/retry handling.
- `audit-logging`: Append-only audit trail of every state-changing action (manual and system), with before/after state and 7-year retention.
- `reporting-dashboard`: Dashboard summary and the Aging, Collections, and Customer Statement reports.
- `user-access-control`: Internal username/password authentication and role-based access control (Admin / Finance Staff / Viewer).

### Modified Capabilities
(none — this is the initial set of specs; no existing capabilities to modify)

## Impact

- **New system**: no existing code in this repo; this change defines the specs the initial implementation will be built against.
- Affects future API surface (`/customers`, `/invoices`, `/invoices/{id}/payments`, `/invoices/{id}/reminders`, `/reports/*`, `/dashboard/summary`, `/audit-log` per `invoice-reminder-spec.md` Section 10).
- Affects future data model (PostgreSQL schema per `invoice-reminder-spec.md` Section 11) and background dispatch worker (reminder scheduler).
- Source document: `invoice-reminder-spec.md` (kept in place, unmodified, as the original narrative draft; these specs are the OpenSpec-formatted, decision-resolved successor).
