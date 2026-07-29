# Invoice Reminder System - OpenSpec Complete Package

**Generated**: 2024
**Source Specification**: invoice-reminder-spec.md (v1 Draft)
**Format**: OpenSpec (OpenAPI 3.0 + Domain Model + Event Flows + Test Automation)

---

## 📦 Package Contents

### Core Specification Files

#### 1. **openapi_spec.json / openapi_spec.yaml**
- **Type**: RESTful API Specification (OpenAPI 3.0.0)
- **Endpoints**: 15 
  - Authentication (login, logout)
  - Customers (CRUD)
  - Invoices (create, issue, edit, cancel)
  - Payments (record, list)
  - Reminders (view, cancel, reschedule)
  - Reports (aging, collections)
  - Dashboard & Audit logs
- **Schemas**: 18 domain models with validation rules
- **Security**: JWT Bearer + Basic Auth
- **Use For**: API documentation, frontend integration, code generation

#### 2. **domain_model_spec.json / domain_model_spec.yaml**
- **Type**: Domain Model & Business Rules Specification
- **Entities**: 9
  1. Customer (soft-delete, contact management)
  2. Invoice (core entity, line items, snapshots)
  3. InvoiceLineItem (products/services, tax-aware)
  4. Payment (recorded payments, method tracking)
  5. ReminderRule (5-rule fixed schedule config)
  6. ReminderInstance (scheduled reminders)
  7. TaxRate (tax configuration with snapshots)
  8. User (staff with role-based access)
  9. AuditLogEntry (immutable change log)
- **Business Rules**: 
  - Status transitions (Draft → Issued → Partially Paid → Paid / Cancelled)
  - Invoice immutability (locked when fully paid)
  - Tax snapshots (frozen at issuance)
  - Reminder cancellation (atomic with payment)
  - Audit trail completeness
- **Invariants**: 6 critical system invariants
- **Use For**: Database schema design, validation logic, implementation

#### 3. **event_flow_testing_spec.json / event_flow_testing_spec.yaml**
- **Type**: Event Flows & Test Specifications
- **Event Flows**: 5
  1. Invoice Creation & Issuance (Draft → Issued with reminder scheduling)
  2. Payment & Status Transition (automatic state changes)
  3. Reminder Scheduling & Dispatch (background job with idempotency)
  4. Invoice Editing (with reminder recalculation)
  5. Invoice Cancellation (with guardrails)
- **Test Specifications**:
  - Unit tests (tax calculation, transitions, constraints)
  - Integration tests (payment → cancellation, editing)
  - End-to-end tests (full workflows)
  - Pinchtab scenarios (browser automation)
- **Performance Targets**:
  - Invoice creation: <1s
  - Dashboard: <2s
  - Reports: <2s
  - Payment: <500ms
- **Use For**: QA planning, test development, workflow validation

#### 4. **pinchtab_tests.json / pinchtab_tests.yaml**
- **Type**: Browser Automation Test Scripts (Pinchtab Framework)
- **Test Suites**: 7
  1. Authentication Tests (3 tests)
  2. Invoice Creation Tests (4 tests)
  3. Payment Tests (4 tests)
  4. Invoice Editing Tests (3 tests)
  5. Dashboard Tests (3 tests)
  6. Audit Log Tests (2 tests)
  7. Reminder Tests (2 tests)
- **Total Tests**: 21 scenarios
- **Coverage**: 
  - User authentication and session management
  - Invoice lifecycle (draft → issued → paid)
  - Payment processing and reconciliation
  - Reminder lifecycle and cancellation
  - Dashboard metrics and reports
  - Audit trail verification
- **Helpers**: Reusable functions for common operations
- **Test Data**: Sample customers, users, fixtures
- **Use For**: End-to-end automated browser testing

#### 5. **SPECIFICATION_SUMMARY.json / SPECIFICATION_SUMMARY.yaml**
- **Type**: Executive Summary
- **Contents**:
  - Overview and system description
  - File descriptions and use cases
  - Key design decisions (11 total)
  - Critical invariants and constraints
  - Open questions from original spec (11 items)
  - Architecture components
  - Success metrics
  - Next steps for implementation
- **Use For**: Quick reference, stakeholder review, project planning

### Documentation

#### 6. **README.md**
- Complete guide to all specifications
- How to use each file
- Event flow diagrams
- Performance targets
- Open questions requiring stakeholder input
- Architecture stack
- Testing strategy
- Next steps for implementation
- Version history

#### 7. **MANIFEST.md** (this file)
- Package contents and file directory
- Quick reference guide
- Implementation roadmap

---

## 🎯 Quick Start Guide

### For API Documentation
→ Start with **openapi_spec.json** (OpenAPI 3.0 format, compatible with Swagger, ReDoc, etc.)

### For Database Design
→ Start with **domain_model_spec.json** (9 entities, business rules, invariants)

### For Development Planning
→ Start with **event_flow_testing_spec.json** (5 workflows, detailed step-by-step)

### For Testing
→ Start with **pinchtab_tests.json** (19 automated test scenarios)

### For Stakeholder Review
→ Start with **SPECIFICATION_SUMMARY.json** + **README.md** + **MANIFEST.md**

---

## 🔑 Key Features at a Glance

✅ **Invoice Management**
- Create, issue, edit, cancel
- Line items with automatic tax calculation
- Customer snapshot (immutable denormalized copy)
- Fixed-point decimal arithmetic (no float errors)

✅ **Payment Tracking**
- Partial and full payment recording
- Manual entry only (no gateway integration)
- Duplicate entry detection
- Automatic status transitions

✅ **Automatic Reminders**
- Fixed 5-rule schedule: -3d, on-due, +7d, +14d, +30d
- Scheduled at invoice issuance
- Recalculated if due date edited
- **Atomically cancelled when fully paid** (prevents false reminders)
- Never duplicated, never sent after payment

✅ **Compliance & Audit**
- Immutable append-only audit log
- Every action logged with actor, timestamp, before/after state
- Tax snapshots (changes don't retroactively affect invoices)
- Role-based access control (Admin/FinanceStaff/Viewer)

✅ **Reporting & Dashboard**
- Dashboard: outstanding balance, overdue count, upcoming due
- Aging report: 0-30, 31-60, 61-90, 90+ days
- Collections report: by period and payment method
- Customer statements
- Full audit log with filtering

---

## 🚨 Critical Invariants (Must be enforced!)

1. **Reminder Safety**: Never send after Paid or Cancelled
2. **No Duplicates**: Max one send per (invoice, rule)
3. **Atomic Payment**: When fully paid, cancel all scheduled reminders in same transaction
4. **Edit Guardrail**: Cannot reduce invoice total below payments received
5. **Tax Snapshots**: Tax rates frozen at issuance, changes don't affect old invoices
6. **Audit Completeness**: Every state change logged with full context

---

## 🏗️ Architecture Stack

| Component | Choice | Notes |
|-----------|--------|-------|
| Frontend | React + TypeScript | Staff-facing UI |
| API | FastAPI (Python) | RESTful, async-ready |
| Database | PostgreSQL | Encrypted at rest, backups |
| Job Queue | Celery | Task scheduling & execution |
| Broker | Redis | Celery broker & Beat scheduler |
| Email | AWS SES | Reliable outbound email |
| Cloud | AWS | Fargate, RDS, ElastiCache, CloudWatch |
| Testing | Pinchtab | Browser automation |
| Unit/Integration | pytest | Python testing framework |

---

## 📊 Performance Targets

| Operation | Target | Rationale |
|-----------|--------|-----------|
| Invoice creation | <1s | Frequent staff action |
| Dashboard queries | <2s | Daily business use |
| Report generation | <2s | Export/analysis need |
| Payment recording | <500ms | Time-sensitive action |
| Reminder dispatch | <5s/100 reminders | Background job SLA |

---

## ❓ Open Questions (Require Stakeholder Input)

These 11 items must be answered before full implementation:

1. **Overpayment**: Reject / allow with credit / allow with warning?
2. **Cancellation refunds**: Refund/credit-note flow in v1?
3. **Missed reminders**: Bounded catch-up window or skip to next?
4. **Email failures**: Max retries and alert threshold?
5. **Tax scope**: Global flat or per-line/customer/category?
6. **Authentication**: Password only or MFA/SSO required?
7. **Reports**: Aging + Collections + Statement, or add Tax Summary?
8. **Retention**: 6-8 years per Indian norms?
9. **Rounding**: Round-half-up to 2 decimals?
10. **Due date**: End-of-day IST or specific time?
11. **Invoice numbering**: At Draft or at Issue?

---

## 🧪 Testing Coverage

### Unit Tests
- Tax calculation (various rates, edge cases)
- Status transitions (valid/invalid paths)
- Constraint validation (unique, FK, etc.)

### Integration Tests
- Full invoice → payment → paid workflow
- Payment triggering reminder cancellation
- Due date edit and reminder recalculation
- Audit log entry generation

### End-to-End (Pinchtab)
- 19 browser automation test scenarios
- Authentication, invoice lifecycle, payments
- Dashboard, reports, audit log verification

### Performance Tests
- Dashboard response time
- Report query performance
- Reminder dispatch throughput

---

## 📋 Implementation Roadmap

### Phase 1: Setup & Planning (Days 1-3)
- [ ] Stakeholder review of all specifications
- [ ] Answer 11 Open Questions
- [ ] Approve architecture and tech stack
- [ ] Set up development environment

### Phase 2: Domain & API (Days 4-10)
- [ ] Create PostgreSQL schema from domain_model_spec
- [ ] Implement Pydantic models (Python dataclasses)
- [ ] Build FastAPI endpoints from openapi_spec
- [ ] Set up Celery tasks for reminder dispatch

### Phase 3: Frontend & Automation (Days 11-15)
- [ ] Build React components for invoice workflows
- [ ] Implement Pinchtab browser tests
- [ ] Set up CI/CD pipeline
- [ ] Create test data fixtures

### Phase 4: Testing & Optimization (Days 16-18)
- [ ] Run all unit/integration tests
- [ ] Run Pinchtab end-to-end tests
- [ ] Performance testing and optimization
- [ ] Security audit and hardening

### Phase 5: Deployment & Monitoring (Days 19-21)
- [ ] Deploy to AWS infrastructure
- [ ] Set up CloudWatch alarms
- [ ] Configure database backups
- [ ] Monitor reminder scheduler uptime

---

## 📁 File Format Reference

All specifications are available in **both JSON and YAML** formats:

- **JSON**: Machine-readable, compatible with most tools
- **YAML**: Human-readable, better for documentation

Choose based on your preference or tooling requirements.

---

## ✅ Specification Quality Checklist

- [x] **Completeness**: 9 entities fully specified
- [x] **Consistency**: Event flows map to API endpoints
- [x] **Testability**: 19 test scenarios covering critical paths
- [x] **Auditability**: Complete audit trail specification
- [x] **Performance**: Clear SLAs and targets defined
- [x] **Security**: RBAC and authentication specified
- [x] **Scalability**: Architecture supports future growth
- [x] **Documentation**: Comprehensive with examples

---

## 🔗 Cross-References

**openapi_spec** → defines HTTP contracts
↓
**domain_model_spec** → defines data structures backing those contracts
↓
**event_flow_testing_spec** → defines workflows exercising those models
↓
**pinchtab_tests** → defines browser scenarios validating those workflows

---

## 📞 Support & Questions

For questions about this specification:
1. Review the relevant spec file (JSON or YAML)
2. Check README.md for detailed explanations
3. Reference event_flow_testing_spec for workflow details
4. Review Open Questions section for unresolved items

---

**Status**: ✅ Ready for implementation
**Version**: 1.0.0
**Generated**: 2024
**Source**: invoice-reminder-spec.md (v1 Draft)

