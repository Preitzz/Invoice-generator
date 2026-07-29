# Invoice Reminder System - OpenSpec Documentation

## Overview

This is a complete **OpenSpec** specification for a **Single-Tenant Invoice Management System with Automatic Payment Reminders**.

Generated: 2026-07-29T04:47:47.250150
Source: invoice-reminder-spec.md (v1 Draft)

## Files Included

### 1. **openapi_spec.json / openapi_spec.yaml**
   - RESTful API specification (OpenAPI 3.0)
   - 15 endpoints covering authentication, customers, invoices, payments, reminders, reports
   - 18 schema definitions with validation rules
   - Use case: Integration, API documentation, code generation

### 2. **domain_model_spec.json / domain_model_spec.yaml**
   - Complete domain model with 9 entities
   - Business rules, constraints, and invariants
   - Lifecycle diagrams and state machines
   - Tax calculation rules and audit requirements
   - Use case: Database design, validation logic, implementation guide

### 3. **event_flow_testing_spec.json / event_flow_testing_spec.yaml**
   - 5 event flows (Invoice Creation, Payment, Reminder Dispatch, Editing, Cancellation)
   - Unit tests (tax calculation, status transitions)
   - Integration tests (full workflows, atomic operations)
   - End-to-end scenarios
   - Performance targets and SLAs
   - Use case: QA planning, test case development

### 4. **pinchtab_tests.json / pinchtab_tests.yaml**
   - 19 browser automation tests across 7 test suites
   - Authentication, invoice lifecycle, payments, reminders
   - Dashboard and audit log tests
   - Helper functions for common operations
   - Use case: End-to-end browser-based automated testing

### 5. **SPECIFICATION_SUMMARY.json / SPECIFICATION_SUMMARY.yaml**
   - Executive summary of all specifications
   - Key design decisions and critical invariants
   - Architecture components
   - Open questions from original spec
   - Next steps for implementation

---

## Key Features Specified

✅ **Invoice Management**
  - Create, issue, edit, cancel invoices
  - Multiple line items with tax calculation
  - Customer snapshot (name/email/address at issuance)
  - Fixed-point decimal arithmetic (no float errors)

✅ **Payment Tracking**
  - Partial and full payment recording
  - Manual entry only (no gateway integration)
  - Duplicate entry detection
  - Automatic status transitions (Draft → Issued → Partially Paid → Paid)

✅ **Automatic Reminders**
  - Fixed 5-rule schedule: -3d, on-due, +7d, +14d, +30d
  - Scheduled during invoice issuance
  - Recalculated if due date edited
  - **Atomically cancelled when invoice fully paid** (critical for data integrity)
  - Never sent twice, never sent after payment

✅ **Compliance & Audit**
  - Immutable append-only audit log
  - Every action logged with actor, timestamp, before/after state
  - Tax rate snapshots (changes don't retroactively affect invoices)
  - Role-based access control (Admin/FinanceStaff/Viewer)

✅ **Reporting**
  - Dashboard summary (outstanding, overdue, upcoming due)
  - Aging report (0-30, 31-60, 61-90, 90+ days overdue)
  - Collections report (by period and payment method)
  - Customer statements
  - Audit log with filtering

---

## Critical Invariants

These **must** be enforced to prevent bugs:

1. **Reminder Safety**: Reminders MUST NEVER be sent after an invoice is Paid or Cancelled
2. **No Duplicates**: A reminder for the same (invoice, rule) pair must never be sent twice
3. **Atomic Payment**: When an invoice reaches full payment, all scheduled reminders cancelled in same transaction
4. **Edit Guardrail**: Cannot reduce invoice total below sum of received payments
5. **Tax Snapshots**: Tax rates snapshotted at issuance; later changes don't affect old invoices
6. **Audit Completeness**: Every state change logged with full before/after context

---

## Event Flow: Invoice Lifecycle

```
1. Draft Creation
   ├─ Customer created
   ├─ Invoice with line items
   └─ Tax calculated (no snapshots yet)

2. Issuance
   ├─ Status: Draft → Issued
   ├─ Tax & totals snapshotted (immutable)
   ├─ 5 ReminderInstances created & scheduled
   ├─ Invoice emailed to customer
   └─ Audit logged

3. Payment (Partial)
   ├─ Payment recorded
   ├─ Status: Issued → Partially Paid
   ├─ Reminders remain Scheduled
   └─ Audit logged

4. Payment (Full)
   ├─ Payment recorded (amount_paid == total_amount)
   ├─ Status: Partially Paid → Paid
   ├─ ALL Scheduled reminders → Cancelled (atomic!)
   └─ Audit logged (payment + 5 cancellations)

5. Reminder Dispatch (Background Job)
   ├─ Scheduler queries Scheduled reminders
   ├─ Double-check: invoice NOT Paid or Cancelled (race condition prevention)
   ├─ Send email (idempotent)
   ├─ Update status to Sent
   └─ Retry on failure (exponential backoff, max 3 retries)
```

---

## Performance Targets

| Operation | Target | Why |
|-----------|--------|-----|
| Invoice creation | <1s | Staff creates frequently |
| Dashboard queries | <2s | Daily business need |
| Report queries | <2s | Data export requirement |
| Payment recording | <500ms | Time-sensitive operation |
| Reminder dispatch | <5s per 100 reminders | Background job SLA |

---

## Open Questions (from original spec)

The following 11 questions **must be answered** by stakeholders before full implementation:

1. Overpayment handling: reject / allow with credit / allow with warning?
2. Cancellation with payments: refund/credit-note flow needed in v1?
3. Missed reminder catch-up: bounded window or skip to next?
4. Email failure retry: max attempts and alert threshold?
5. Tax scope: global flat rate or per-line-item/customer/category?
6. Authentication: password only or MFA/SSO required?
7. Reports: Aging + Collections + Customer Statement, or add Tax Summary?
8. Data retention: 6-8 years per Indian financial norms?
9. Rounding: round-half-up to 2 decimals (paisa)?
10. Due date precision: end-of-day IST or specific time?
11. Invoice numbering: at Draft creation or at Issue?

---

## Architecture Stack

- **Frontend**: React + TypeScript
- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL (encrypted at rest)
- **Job Queue**: Celery + Redis
- **Email**: AWS SES
- **Cloud**: AWS (Fargate, RDS, ElastiCache, CloudWatch)
- **Testing**: Pinchtab (browser), pytest (unit/integration)

---

## Testing Strategy

### Unit Tests (pytest)
- Tax calculation with various rates
- Status transition validation
- Constraint checking (UNIQUE, FK, etc.)

### Integration Tests (pytest)
- Full invoice → payment → paid workflow
- Payment triggering reminder cancellation
- Due date edit and reminder recalculation

### End-to-End Tests (Pinchtab)
- 19 browser automation tests
- Authentication, invoice creation, payment, reports
- Audit log verification

### Performance Tests
- Dashboard response time
- Report query time
- Reminder dispatch throughput

---

## How to Use These Specifications

### For Frontend Developers
1. Read `openapi_spec.json` for API contracts
2. Reference `pinchtab_tests.json` for happy/sad paths
3. Implement UI based on test scenarios

### For Backend Developers
1. Read `domain_model_spec.json` for entities and business rules
2. Read `event_flow_testing_spec.json` for workflow details
3. Implement FastAPI routes from `openapi_spec.json`
4. Implement Celery tasks for reminder dispatch

### For Database Architects
1. Read Section 11 of original spec (database schema)
2. Reference `domain_model_spec.json` for constraints
3. Design migrations for audit log (append-only)

### For QA/Testers
1. Read `event_flow_testing_spec.json` for test scenarios
2. Read `pinchtab_tests.json` for automation scripts
3. Create test data fixtures
4. Run full test suite before release

### For DevOps/SRE
1. Configure CloudWatch alarms for reminder scheduler heartbeat
2. Set up automatic backups for PostgreSQL
3. Configure encryption at rest for sensitive data
4. Monitor Celery task latency and failure rates

---

## Key Success Criteria

✅ **Critical (0 tolerance)**
- 0 reminders sent after invoice Paid/Cancelled
- 0 duplicate reminders for same invoice
- 100% tax rounding consistency

✅ **Important**
- <2s dashboard response time
- <500ms payment recording
- Complete audit trail for all state changes

✅ **Business Metrics**
- Measurable reduction in DSO (Days Sales Outstanding)
- Reduced manual reminder effort

---

## Next Steps

1. **Stakeholder Review**: Get approval on 11 Open Questions
2. **Detailed Design**: Use specs as input for technical design
3. **Implementation**: Develop against these specs
4. **Testing**: Run Pinchtab tests in CI/CD pipeline
5. **Deployment**: Monitor reminder scheduler on production
6. **Optimization**: Gather metrics and improve based on actual usage

---

## Version History

- **v1.0.0** (Generated 2026-07-29T04:47:47.250150)
  - Initial OpenSpec generation from invoice-reminder-spec.md (v1 Draft)
  - 6 specification files (JSON + YAML formats)
  - 15 API endpoints, 9 domain entities, 19 test scenarios

---

**Generated by**: OpenSpec Generator v1.0.0
**Source Document**: invoice-reminder-spec.md (Draft)
**Status**: Ready for stakeholder review and implementation planning
