## Purpose

Give staff visibility into outstanding receivables and payment activity through a summary dashboard and a fixed set of financial reports.

## ADDED Requirements

### Requirement: Dashboard summary
The system SHALL provide a dashboard summary showing total outstanding balance, count of overdue invoices, upcoming due invoices, and recently received payments.

#### Scenario: Dashboard reflects current state
- **WHEN** a staff member opens the dashboard
- **THEN** the system displays the current total outstanding balance across all non-`Paid`, non-`Cancelled` invoices, the count of currently `Overdue` invoices, invoices due in the near future, and the most recently recorded payments

### Requirement: Report scope limited to Aging, Collections, and Customer Statement
The system SHALL provide exactly three reports in v1: an Aging report, a Collections report, and a Customer Statement report. No Tax Summary report is provided in v1.

**Decision:** The report list is Aging + Collections + Customer Statement only, with no Tax Summary (Section 14, Q7). A Tax Summary report was judged unnecessary in v1 given the single global flat-tax model (no GST/multi-rate complexity to reconcile); it may be reconsidered if the tax model becomes more complex in a future version.

#### Scenario: Aging report buckets outstanding invoices
- **WHEN** a staff member requests the Aging report
- **THEN** the system returns outstanding (non-`Paid`, non-`Cancelled`) invoices grouped into 0-30, 31-60, 61-90, and 90+ days overdue buckets, based on the derived `Overdue` calculation

#### Scenario: Collections report shows payments in a period
- **WHEN** a staff member requests the Collections report for a given date range
- **THEN** the system returns all payments recorded with `payment_date` within that range

#### Scenario: Customer statement lists a customer's invoice and payment history
- **WHEN** a staff member requests the statement for a specific customer
- **THEN** the system returns that customer's invoices and associated payments, including cancelled and fully paid ones, for historical reference

#### Scenario: Tax Summary is not offered
- **WHEN** a staff member looks for a Tax Summary report in the reports list
- **THEN** no such report exists in v1
