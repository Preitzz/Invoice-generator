## Purpose

Maintain the authoritative record of customers who receive invoices, while guaranteeing that historical invoices and reminders are never affected by later edits or deletion of a customer record.

## ADDED Requirements

### Requirement: Customer CRUD
The system SHALL allow authorized staff to create, view, and update customer records containing name, email, phone, and billing address.

#### Scenario: Create a customer
- **WHEN** an authorized staff member submits a new customer with name, email, phone, and billing address
- **THEN** the system creates a customer record with a unique id, `is_active = true`, and `created_at`/`updated_at` timestamps

#### Scenario: Update a customer
- **WHEN** an authorized staff member edits an existing customer's name, email, phone, or billing address
- **THEN** the system updates the customer record and its `updated_at` timestamp
- **AND** no existing invoice's snapshotted customer data is modified

### Requirement: Soft-delete only
The system SHALL support only soft-deletion of customers (`is_active = false`); hard deletion is never permitted while the customer has any invoice not in `Paid` or `Cancelled` status.

#### Scenario: Block hard delete with open invoices
- **WHEN** a staff member attempts to delete a customer who has at least one invoice with status other than `Paid` or `Cancelled`
- **THEN** the system rejects the hard-delete request and, if a delete action is issued, converts it to a soft-delete (`is_active = false`)

#### Scenario: Soft-delete leaves history intact
- **WHEN** a customer with only `Paid` or `Cancelled` invoices is soft-deleted
- **THEN** the customer's `is_active` flag becomes `false`
- **AND** all of that customer's historical invoices, line items, payments, and reminder instances remain unchanged and queryable

### Requirement: Invoice snapshot of customer data
The system SHALL copy (denormalize) the customer's name, email, and billing address onto the invoice at issuance time, and SHALL use only that snapshot for all future rendering, emailing, and reporting of that invoice — never a live lookup of the customer record.

#### Scenario: Customer edited after invoice issuance
- **WHEN** a customer's email or address is edited after one of their invoices has been issued
- **THEN** the previously issued invoice continues to display and send reminders to the snapshotted email/address captured at issuance, unaffected by the edit

#### Scenario: Reminder email uses snapshot for soft-deleted customer
- **WHEN** a reminder is dispatched for an invoice whose customer has since been soft-deleted
- **THEN** the reminder is sent to the invoice's snapshotted customer email, not blocked or redirected by the customer's `is_active` state
