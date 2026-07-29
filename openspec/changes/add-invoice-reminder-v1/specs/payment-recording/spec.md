## Purpose

Let staff manually record payments received against an invoice, ensure recorded payments never exceed what is owed, and derive invoice payment status consistently from those records.

## ADDED Requirements

### Requirement: Manual payment entry
The system SHALL allow authorized staff to manually record a payment against an invoice, capturing amount, payment date, method (cash / bank transfer / UPI / cheque), optional notes, and the recording staff member.

#### Scenario: Record a valid payment
- **WHEN** a staff member records a payment of an amount less than or equal to the invoice's outstanding balance
- **THEN** the system creates a payment record linked to the invoice with `recorded_by` set to the acting staff member
- **AND** the invoice's `amount_paid` increases by the payment amount

### Requirement: Overpayment rejected outright
The system SHALL validate that `amount_paid + new_payment <= total_amount` and SHALL reject any payment that would cause `amount_paid` to exceed `total_amount`. No credit balance is tracked in v1.

**Decision:** Overpayment is rejected outright (Section 14, Q1), rather than allowed with a tracked credit balance or allowed with only a warning. This keeps `amount_paid` always bounded by `total_amount`, simplifying status derivation and avoiding the need for a credit-balance ledger in v1.

#### Scenario: Payment exceeding outstanding balance is rejected
- **WHEN** a staff member attempts to record a payment where `amount_paid + new_payment > total_amount`
- **THEN** the system rejects the payment and no payment record is created
- **AND** the invoice's `amount_paid` is unchanged

#### Scenario: Payment exactly matching outstanding balance is accepted
- **WHEN** a staff member records a payment where `amount_paid + new_payment == total_amount`
- **THEN** the system accepts the payment and the invoice status becomes `Paid`

### Requirement: Duplicate payment detection
The system SHALL warn staff before accepting a payment that appears to duplicate an existing payment on the same invoice — same amount recorded within a short time window — using a heuristic check, since there is no payment-gateway idempotency key.

#### Scenario: Likely duplicate payment surfaces a warning
- **WHEN** a staff member attempts to record a payment with the same amount as a payment already recorded on the same invoice within the configured short time window
- **THEN** the system surfaces a warning requiring explicit confirmation before the second payment is recorded
- **AND** if confirmed, the system still enforces the overpayment validation before accepting it

### Requirement: Status transition driven by recorded payments
The system SHALL transition an invoice's status to `Partially Paid` when `0 < amount_paid < total_amount`, and to `Paid` the moment `amount_paid == total_amount`.

#### Scenario: Partial payment moves status to Partially Paid
- **WHEN** a payment is recorded that brings `amount_paid` above zero but below `total_amount`
- **THEN** the invoice status becomes `Partially Paid`
- **AND** reminders continue on the existing schedule

#### Scenario: Final payment moves status to Paid and stops reminders
- **WHEN** a payment is recorded that brings `amount_paid` to exactly `total_amount`
- **THEN** the invoice status becomes `Paid`
- **AND** all remaining scheduled reminder instances for that invoice are immediately cancelled
