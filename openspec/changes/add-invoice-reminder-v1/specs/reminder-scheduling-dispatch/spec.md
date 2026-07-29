## Purpose

Guarantee that payment reminder emails are scheduled on a fixed policy, sent exactly once, stopped the instant an invoice is fully paid or cancelled, and recovered predictably after scheduler downtime or delivery failure.

## ADDED Requirements

### Requirement: Fixed-schedule reminder generation on issuance
The system SHALL, at the moment an invoice is issued, schedule five reminder instances against the fixed policy: 3 days before due, on the due date, and 7, 14, and 30 days after the due date.

#### Scenario: Issuing an invoice schedules all five reminders
- **WHEN** a Draft invoice is issued with a due date
- **THEN** the system creates five `ReminderInstance` records (before_due_3d, on_due, overdue_7d, overdue_14d, overdue_30d), each `scheduled_for` computed from the due date, all in `scheduled` status

### Requirement: Reminder recalculation on due-date edit
The system SHALL recalculate all not-yet-sent (`scheduled`) reminder instances when an invoice's due date is edited, while already-`sent` reminder instances remain unchanged as historical record.

#### Scenario: Due date changed before any reminder sent
- **WHEN** an invoice's due date is edited and no reminder instance has yet been sent
- **THEN** all `scheduled` reminder instances are recomputed against the new due date

#### Scenario: Due date changed after some reminders already sent
- **WHEN** an invoice's due date is edited after one or more reminder instances have already been sent
- **THEN** the already-`sent` instances are left untouched
- **AND** only the remaining `scheduled` instances are recalculated against the new due date

### Requirement: Exactly-once reminder dispatch
The system SHALL send each reminder instance exactly once, enforced by an atomic claim-before-send pattern (a unique `(invoice_id, rule_id)` constraint and a row-level claim such as `UPDATE ... WHERE status='scheduled' RETURNING`) so that concurrent or retried dispatch attempts can never send the same instance twice. Immediately before sending, the system SHALL re-verify within the same transaction that the invoice is not already `Paid` or `Cancelled`.

#### Scenario: Concurrent dispatch attempts send only once
- **WHEN** two dispatch workers concurrently attempt to send the same `scheduled` reminder instance
- **THEN** exactly one worker successfully claims and sends it; the other observes it already claimed and takes no action

#### Scenario: Payment races reminder dispatch
- **WHEN** an invoice becomes fully paid in the same window a reminder for it is about to be dispatched
- **THEN** the dispatch transaction re-checks invoice status immediately before sending and, finding it `Paid`, cancels the reminder instead of sending it

### Requirement: Reminder cancellation on full payment or invoice cancellation
The system SHALL cancel all remaining `scheduled` reminder instances for an invoice the instant it becomes `Paid` or `Cancelled`, and SHALL record the cancellation as an audited event with a reason (`invoice paid`, `invoice cancelled`, or `manual override`). Cancelled instances are retained, not deleted.

#### Scenario: Full payment cancels remaining reminders
- **WHEN** an invoice transitions to `Paid`
- **THEN** every remaining `scheduled` reminder instance for that invoice transitions to `cancelled` with reason `invoice paid`, retained for audit history

#### Scenario: Admin manually cancels a single reminder
- **WHEN** an Admin manually cancels one individual scheduled reminder instance
- **THEN** that instance transitions to `cancelled` with reason `manual override`, and the action is recorded in the audit log

### Requirement: Bounded 24-hour catch-up for missed reminders
The system SHALL, upon scheduler recovery after downtime, send any `scheduled` reminder instance whose `scheduled_for` time is within the last 24 hours (catch-up window), and SHALL skip (leave `scheduled`, deferring to its next natural dispatch pass — effectively merging into the next scheduled reminder) any instance whose `scheduled_for` time is more than 24 hours in the past, rather than sending it late outside the window.

**Decision:** A bounded 24-hour catch-up window was chosen (Section 14, Q3) over unconditional late-send or unconditional skip: it keeps reminders timely enough to still be useful to the recipient while avoiding sending a confusing, wildly-late reminder (e.g. an "on due date" notice arriving a week late). Anything older than 24 hours is superseded by the next scheduled reminder in the fixed sequence.

#### Scenario: Scheduler recovers within the catch-up window
- **WHEN** the scheduler restarts and finds a `scheduled` reminder instance whose `scheduled_for` was 6 hours in the past
- **THEN** the system dispatches it now (subject to the standard exactly-once claim and payment re-verification)

#### Scenario: Scheduler recovers outside the catch-up window
- **WHEN** the scheduler restarts and finds a `scheduled` reminder instance whose `scheduled_for` was 40 hours in the past
- **THEN** the system does not send that instance late; it is skipped in favor of the next reminder due in the fixed sequence, and the skip is recorded in the audit log

### Requirement: Email failure retry policy and Admin alert
The system SHALL retry a failed reminder email delivery up to 3 times automatically with exponential backoff. If all 3 retries fail, the system SHALL mark the reminder instance permanently `Failed` and SHALL alert an Admin for manual follow-up.

**Decision:** 3 automatic retries with backoff, then permanent-Failed plus Admin alert (Section 14, Q4) balances resilience to transient delivery issues (e.g. temporary SMTP/API errors) against not silently losing a reminder — a human is always notified when automated delivery is exhausted.

#### Scenario: Transient failure recovers on retry
- **WHEN** a reminder email delivery attempt fails and a retry within the 3-attempt budget succeeds
- **THEN** the reminder instance transitions to `sent` and `attempt_count` reflects the number of attempts made

#### Scenario: All retries exhausted
- **WHEN** a reminder email delivery fails on all 3 automatic retry attempts
- **THEN** the reminder instance transitions to permanently `Failed`
- **AND** an alert is raised to an Admin user for manual follow-up

### Requirement: Emergency reminder kill-switch
The system SHALL provide a single global kill-switch flag, checked immediately before every dispatch attempt, that allows an Admin to halt all outgoing reminder emails instantly without a code deployment.

#### Scenario: Kill-switch halts all dispatch
- **WHEN** the global reminder kill-switch is enabled
- **THEN** no reminder instance is dispatched, regardless of its `scheduled_for` time, until the kill-switch is disabled
