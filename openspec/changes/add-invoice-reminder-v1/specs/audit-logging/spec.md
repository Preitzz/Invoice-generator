## Purpose

Provide a tamper-evident, append-only record of every financial state change — manual or system-driven — sufficient for statutory financial record-keeping and internal review.

## ADDED Requirements

### Requirement: Append-only audit log of every state-changing action
The system SHALL record every state-changing action (customer create/update/soft-delete, invoice create/edit/issue/cancel, payment recorded, reminder scheduled/sent/cancelled/failed, manual override) as an append-only audit log entry containing entity type, entity id, action, actor (nullable, meaning "system"), before-state, after-state, and timestamp. No update or delete operation SHALL ever be permitted on audit log entries.

#### Scenario: Manual action is audited
- **WHEN** a staff member edits an invoice
- **THEN** an audit log entry is created recording the actor's id, `entity_type = invoice`, the action, and the before/after state of the changed fields

#### Scenario: System action is audited with system actor
- **WHEN** the reminder scheduler automatically cancels a reminder instance because an invoice was fully paid
- **THEN** an audit log entry is created with `actor_id = null` (system), the reason, and the before/after state of the reminder instance

#### Scenario: Audit entries cannot be modified or deleted
- **WHEN** any process, including an Admin, attempts to update or delete an existing audit log entry
- **THEN** the system rejects the operation; the audit table grants no UPDATE or DELETE privileges

### Requirement: 7-year retention of financial records
The system SHALL retain invoices, payments, and audit log entries for a minimum of 7 years from creation, consistent with Indian financial record-keeping norms, and SHALL NOT provide any mechanism to purge or hard-delete these records before that retention period elapses.

**Decision:** 7-year retention was selected (Section 14, Q8) as the applicable Indian financial record-keeping norm (within the commonly cited 6-8 year range) for invoices, payments, and audit logs, absent a more specific statutory requirement for this business.

#### Scenario: Records within retention period are never purged
- **WHEN** any scheduled maintenance, cleanup job, or manual admin action attempts to delete an invoice, payment, or audit log entry younger than 7 years
- **THEN** the system blocks the deletion

#### Scenario: Retention applies regardless of invoice status
- **WHEN** an invoice is `Cancelled` or `Paid`
- **THEN** it and its associated payments and audit entries remain retained for the full 7-year period identically to any other invoice status
