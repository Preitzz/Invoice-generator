## Purpose

Define the invoice lifecycle — creation, line items, tax computation, editing, numbering, status derivation, and cancellation — as a deterministic, auditable record of what a customer owes.

## ADDED Requirements

### Requirement: Draft invoice creation with line items
The system SHALL allow staff to create a Draft invoice for a customer with one or more line items, each specifying description, quantity, and unit price.

#### Scenario: Create a draft with multiple line items
- **WHEN** a staff member creates an invoice for a customer with two or more line items
- **THEN** the system stores the invoice in `Draft` status with all line items attached
- **AND** no invoice number is assigned yet

### Requirement: Fixed-point monetary computation with round-half-up rounding
The system SHALL compute subtotal, tax, and total using fixed-point decimal arithmetic only (never floating point), rounding all monetary values to 2 decimal places using round-half-up (nearest paisa).

**Decision:** Round-half-up to 2 decimal places was selected as the single documented rounding rule (Section 14, Q9) because it is unambiguous, matches common invoicing/accounting convention, and is trivially testable with property-based tests (`sum(line items) + tax == total` across randomized inputs).

#### Scenario: Line item and invoice totals round consistently
- **WHEN** an invoice's computed subtotal or tax produces a third decimal digit of 5 or greater
- **THEN** the system rounds that value up to the nearest paisa (2 decimal places)
- **AND** `subtotal + tax_amount == total_amount` holds exactly after rounding

### Requirement: Global flat tax rate, snapshotted at issuance
The system SHALL apply a single global flat tax rate (not per-item, per-customer, or per-product-category) to line items, and SHALL snapshot the effective tax rate onto the invoice and each line item at issuance time so that later changes to the global rate never retroactively alter an already-issued invoice.

**Decision:** Tax rate scope is a single global flat rate (Section 14, Q5), consistent with the locked foundational decision "Tax model: Simple flat rate (not GST)". Per-item/customer variation is out of scope for v1.

#### Scenario: Global tax rate changes after issuance
- **WHEN** the global tax rate is changed after an invoice has already been issued
- **THEN** the previously issued invoice's `tax_amount` and each line item's `tax_rate_snapshot` remain unchanged

### Requirement: Invoice numbering assigned at Issue time
The system SHALL assign the permanent, sequential invoice number (`INV-0001`, `INV-0002`, ...) only when an invoice transitions from `Draft` to `Issued`, not at Draft creation. Numbers are never reused, including for cancelled invoices.

**Decision:** Numbering is assigned at Issue time (Section 14, Q11) specifically to avoid numbering gaps caused by abandoned Draft invoices that are never sent. Gaps from later cancellation of an already-Issued invoice remain expected and acceptable for audit purposes.

#### Scenario: Abandoned draft does not consume a number
- **WHEN** a Draft invoice is created and never issued (left as Draft or deleted)
- **THEN** no invoice number is reserved or consumed for it
- **AND** the next invoice to be Issued receives the next sequential number with no gap attributable to the abandoned draft

#### Scenario: Issuing an invoice assigns its number
- **WHEN** a Draft invoice is issued
- **THEN** the system assigns the next sequential invoice number, snapshots the tax and totals permanently, and transitions status to `Issued`

### Requirement: Invoice editing rules
The system SHALL allow editing an invoice while it is in `Draft`, `Issued`, or `Partially Paid` status (i.e., any time before full payment), and SHALL reject any edit that would reduce the invoice total below the sum of payments already recorded against it. Every edit SHALL be recorded in the audit log with before/after state.

#### Scenario: Edit blocked below recorded payments
- **WHEN** a staff member edits an invoice such that the new total would be less than `amount_paid`
- **THEN** the system rejects the edit and the invoice remains unchanged

#### Scenario: Edit allowed before full payment
- **WHEN** a staff member edits an `Issued` invoice that is not yet fully paid, and the new total is greater than or equal to `amount_paid`
- **THEN** the system applies the edit and records an audit log entry with before/after state

#### Scenario: Edit blocked once fully paid
- **WHEN** a staff member attempts to edit an invoice whose status is `Paid`
- **THEN** the system rejects the edit

### Requirement: Status lifecycle and derived Overdue flag
The system SHALL manage invoice status as `Draft → Issued → Partially Paid → Paid`, with `Cancelled` reachable from `Draft`, `Issued`, or `Partially Paid` only when `amount_paid = 0`. `Overdue` SHALL be a derived, computed flag (`due_date < now AND status not in (Paid, Cancelled)`), never a manually settable stored state. Due-date comparisons SHALL use end-of-day IST (23:59:59 Asia/Kolkata) on the due date as the precise moment an invoice becomes overdue.

**Decision:** Due date precision is end-of-day IST, 23:59:59 Asia/Kolkata (Section 14, Q10) — an invoice is not overdue until the entire due date (in the business's single timezone) has elapsed. All timestamps are stored in UTC; this comparison is performed by explicit conversion to Asia/Kolkata, consistent with the single-business-timezone assumption.

#### Scenario: Invoice becomes Overdue
- **WHEN** the current time is past 23:59:59 Asia/Kolkata on an invoice's due date, and the invoice's status is `Issued` or `Partially Paid`
- **THEN** the invoice is reported as `Overdue` by any query or report that surfaces it, without any stored status transition having occurred

#### Scenario: Overdue flag never applies to Paid or Cancelled invoices
- **WHEN** an invoice's status is `Paid` or `Cancelled`, regardless of due date
- **THEN** the invoice is never reported as `Overdue`

### Requirement: Cancellation blocked once any payment exists
The system SHALL allow cancellation of an invoice only when `amount_paid = 0`. Cancelling an invoice that has any recorded payment SHALL be rejected in v1; there is no refund or credit-note flow — reversal must happen manually outside the system.

**Decision:** Cancellation-with-payments is blocked in v1 with no refund/credit-note flow (Section 14, Q2). A refund/credit-note workflow was judged unnecessary complexity for v1's manual-payment-only model; if a payment was recorded in error, it must be reversed by direct manual correction outside the system (see audit-logging for the compensating record).

#### Scenario: Cancel invoice with no payments
- **WHEN** a staff member cancels a `Draft`, `Issued`, or `Partially Paid` invoice with `amount_paid = 0`
- **THEN** the system transitions the invoice to `Cancelled`, records `cancelled_at` and `cancellation_reason`, and cancels any scheduled reminders

#### Scenario: Cancel blocked once a payment exists
- **WHEN** a staff member attempts to cancel an invoice with `amount_paid > 0`
- **THEN** the system rejects the cancellation request and the invoice status is unchanged
