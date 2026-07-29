# Invoice Generator with Payment-Reminder Engine
## OpenSpec & Implementation Guide — START HERE

**Program:** AI-Native Bridge Program | **Capstone Cluster:** Money, Time & Notifications  
**Status:** Specification Complete & Ready for Implementation  
**Timeline:** 5 weeks to MVP (production-ready)  
**Team Size:** 2–4 engineers

---

## WHAT YOU'RE BUILDING

A **production-grade invoice management system** that:
- ✅ Generates invoices with correct tax calculations
- ✅ Records payments idempotently (no duplicates from webhook retries)
- ✅ Automatically schedules and sends payment reminders
- ✅ Cancels reminders immediately after payment
- ✅ Maintains complete, immutable audit trail
- ✅ Handles edge cases: concurrency, timezone, DST, scheduler failures
- ✅ Recovers from crashes without losing or duplicating reminders

**Not about:** Flashy UI, AI hype, or feature count.  
**Purely about:** Boring, unshakeable correctness under real-world conditions.

---

## DOCUMENTS IN THIS PACKAGE

| Document | Purpose | Read Time |
|----------|---------|-----------|
| **[Invoice-Generator-OpenSpec-Prompt.md](#)** | Complete technical specification (15 sections, 70+ pages) | 4–6 hours |
| **[Implementation-Kickoff-Guide.md](#)** | Phased implementation plan (5 phases, 5 weeks) | 1–2 hours |
| **[Quick-Reference-Card.md](#)** | Developer cheat sheet (formulas, SQL, debugging) | 30 min (bookmark this) |
| **[Architecture-Decisions.md](#)** | ADRs and system architecture diagrams | 2 hours |
| **README-START-HERE.md** | This file — your entry point | 20 min |

---

## QUICK START: 5-MINUTE OVERVIEW

### The Problem
Businesses waste time manually sending payment reminders. They can't trust automation because:
- Reminders are sent even after payment arrives
- Duplicate reminders confuse customers
- Tax calculations are wrong (audit risk)
- No audit trail (compliance failure)
- System crashes lose reminders forever

### The Solution
Automated invoice + reminder system with:
1. **Correctness** — Financial calculations exact to the cent (verified against TaxJar)
2. **Idempotency** — Same payment webhook twice = same result (no double-charges)
3. **Reliability** — Surviving crashes, network outages, scheduler failures
4. **Auditability** — Every state change immutably logged (tax/audit compliance)
5. **Intelligence** — Reminders sent at right time to right person without duplicates

### The Architecture
```
React Dashboard
    ↓
FastAPI (Python) ──→ PostgreSQL (invoices, payments, audit trail)
    ↓                      ↑
Celery Scheduler ─────────┘
    ↓
Email (SendGrid)
    ↑
Stripe/PayPal Webhooks
```

### The Timeline
- **Week 1–2:** Customer management, invoice creation, payment recording
- **Week 3:** Invoice cancellation, status management, reporting
- **Week 4:** Concurrency tests, scheduler resilience, webhook integration
- **Week 5:** Performance tuning, security hardening, production readiness

---

## BEFORE YOU START: ANSWER THESE 10 QUESTIONS

**The spec has 10 open questions that you (the product owner) must answer.**

These are in **Section 14 of the OpenSpec.** Examples:
1. Should we allow overpayment and create credit memos, or reject overpayments?
2. After an invoice is ISSUED, can finance team change the due date?
3. Should users customize reminder schedules per customer, or use global default?

**Why this matters:** These decisions affect code design, database schema, and API contracts.  
**How to answer:** Schedule 30-min meeting with stakeholders; document decisions in spec.

---

## PHASE 0: SETUP (1–2 Days, Before Implementation)

### Environment Checklist
- [ ] Team reads Sections 1–5 of OpenSpec (Product Vision, Requirements, Domain Model)
- [ ] Answer all 10 open questions (Section 14)
- [ ] Confirm technology stack:
  - Backend: FastAPI (Python 3.11+)
  - Database: PostgreSQL 14+
  - Background Jobs: Celery + Redis
  - Frontend (Phase 4): React 18 + TypeScript
  - Cloud: AWS or Azure (recommended)
- [ ] Set up local dev environment:
  ```bash
  git clone <repo>
  python -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
  docker-compose up  # Start PostgreSQL + Redis
  pytest --collect-only  # Verify test framework
  ```
- [ ] Create seed data (5 customers, 10 invoices, 5 payments)
- [ ] Review database schema (Section 11.1); run migrations

### Spec Sign-Off
- [ ] All 10 open questions answered
- [ ] Tax jurisdictions to support finalized (US-CA, US-TX, CA-ON, GB, DE, AU, etc.)
- [ ] Reminder schedule defaults chosen (Early: -7 days, Due: 0, Overdue: +1, Escalation: +7)
- [ ] Email template drafts reviewed
- [ ] Compliance requirements finalized (SOX, GDPR, CCPA?)

---

## IMPLEMENTATION OVERVIEW: 5 PHASES

### PHASE 1 (Weeks 1–2): MVP Core — 40% of project
**What:** Customer management, invoices (draft/issue), payment recording, reminder scheduler  
**Tests:** 97 unit + integration tests  
**Success Criteria:** 85%+ code coverage; all financial calculations verified; idempotency proven  
**Effort:** 2 engineers, full-time

**Deliverables:**
```
✅ API: /customers (CRUD)
✅ API: /invoices (create, issue, query)
✅ API: /invoices/{id}/payments (record, list)
✅ API: /invoices/{id}/status (query, derived)
✅ Background: Reminder scheduler (every 5 min)
✅ Email: Send reminders via SMTP
✅ Database: Full schema with triggers, audit log
✅ Tests: 97 test cases, 85% coverage
```

### PHASE 2 (Week 3): Completeness — 20% of project
**What:** Invoice cancellation, reporting, audit logging  
**Tests:** 26 test cases  
**Success Criteria:** Dashboard KPIs working; audit log immutable; reports accurate

**Deliverables:**
```
✅ API: /invoices/{id}/cancel
✅ API: /dashboard/summary (KPIs)
✅ API: /reports/aging, /reports/reminders, /reports/audit
✅ Tests: 26 test cases, maintain 85% coverage
```

### PHASE 3 (Week 4): Robustness — 20% of project
**What:** Edge cases, concurrency, scheduler resilience, webhook integration  
**Tests:** 50+ test cases (concurrency, failure scenarios)  
**Success Criteria:** All edge cases handled; scheduler survives crashes; webhooks idempotent

**Deliverables:**
```
✅ Concurrency tests: Payment race conditions, reminder + payment collision
✅ Scheduler tests: Crash recovery, lock coordination, queue overload
✅ Webhook integration: Stripe/PayPal handler, signature verification
✅ Edge case tests: Timezone DST, invalid tax, deleted customers
✅ Tests: 50+ test cases, maintain 85% coverage
```

### PHASE 4 (Week 5): Hardening — 15% of project
**What:** Performance tuning, security hardening, monitoring, runbooks  
**Tests:** Load tests, security scans  
**Success Criteria:** p95 latency <300ms; 0 security vulnerabilities; monitoring active

**Deliverables:**
```
✅ Performance: Load test (100 concurrent users); identify bottlenecks
✅ Security: Input validation, SQL injection prevention, rate limiting
✅ Monitoring: CloudWatch/DataDog alerts, dashboards, runbooks
✅ Deployment: Infrastructure-as-Code (Terraform), CI/CD pipeline
```

### PHASE 5 (Optional): Frontend & AI Features — 25% of project
**What:** React dashboard, AI payment delay prediction (if time permits)  
**Effort:** 1–2 engineers  
**Timeline:** 3–4 weeks

---

## CRITICAL SUCCESS FACTORS

### 1. Test-Driven Development
- Write tests BEFORE code
- Target: 85% code coverage; 100% for financial calculations
- Run daily: `pytest -v --cov=app`

### 2. Financial Accuracy (Non-Negotiable)
- All monetary values: `Decimal` type (never `float`)
- Tax calculation: Round to 2 decimals using `ROUND_HALF_UP`
- Verification: Compare 100+ invoices against TaxJar API (<0.01% discrepancy acceptable)

### 3. Idempotency (Non-Negotiable)
- Payment idempotency: Same webhook twice = same payment record
- Reminder idempotency: Each reminder type sent exactly once per invoice
- Implementation: Database constraints + status tracking

### 4. Audit Trail (Non-Negotiable)
- Every state change logged immutably
- Audit log: append-only, NO UPDATE/DELETE allowed
- Compliance: 7-year retention; exportable for audits

### 5. Edge Case Testing
- Concurrency: Parallel payment + reminder send
- Timezone: DST transitions, customer in Sydney/NY/London
- Failure: Scheduler crash, email service down, webhook retry
- See Section 6 of OpenSpec for 40+ scenarios

---

## COMMON PITFALLS (Avoid These!)

| Pitfall | Impact | Prevention |
|---------|--------|-----------|
| Using `float` for money | Wrong tax calculated; audit fails | Always use `Decimal` |
| Forgetting timezone | Reminders sent at wrong time | Test DST transitions |
| No payment idempotency | Duplicate charges | DB unique constraint + check before insert |
| Status manually set | Inconsistent state | Status = calculated from total_paid |
| Editing ISSUED invoices | Tax law violation | DB constraint: read-only after ISSUED |
| Reminders after payment | Customer confusion | Trigger cancels reminders on payment |
| Mutable audit log | Non-compliant | DB role: REVOKE DELETE on audit_log |
| Scheduler duplication | Duplicate reminders sent | Distributed lock (Redis SET NX) |
| No transaction wrapping | Partial failures | Wrap all multi-step ops in transaction |
| Silent calculation errors | Audit discovers fraud | Test every formula; compare to reference |

---

## HOW TO READ THE SPEC

### If You Have 30 Minutes
Read: Section 1 (Vision), Section 2 (Requirements Summary), Section 14 (Open Questions)  
Outcome: Understand the problem, business goals, critical decisions

### If You Have 2 Hours
Read: Sections 1–5 (Vision, Functional Requirements, Non-Functional, Domain Model, Business Rules)  
Outcome: Understand system design, entities, key invariants

### If You Have 4–6 Hours (Recommended)
Read: Entire OpenSpec (Sections 1–13, skim 14)  
Outcome: Complete understanding; ready to implement

### If You Have 30 Seconds (You're in a hurry!)
1. Your job: Answer 10 questions (Section 14)
2. Read Quick-Reference-Card.md (formulas, SQL, debugging tips)
3. Start Phase 1 (Section Implementation-Kickoff-Guide.md)

---

## KEY FORMULAS (Bookmark These)

### Tax Calculation
```python
from decimal import Decimal, ROUND_HALF_UP

taxable_amount = Decimal('0')
for item in line_items:
    if item.tax_category in ('Standard', 'Reduced'):
        taxable_amount += item.quantity * item.unit_price

tax_rate = get_tax_rate(jurisdiction, category)
tax_amount = (taxable_amount * tax_rate).quantize(
    Decimal('0.01'), 
    rounding=ROUND_HALF_UP
)
```

### Reminder Scheduling
```python
from datetime import timedelta
from pytz import timezone as tz

customer_tz = tz(customer.timezone)
due_date = invoice.due_date
offsets = {'EARLY': -7, 'DUE': 0, 'OVERDUE': 1, 'ESCALATION': 7}

for reminder_type, offset in offsets.items():
    send_date = due_date + timedelta(days=offset)
    send_time_local = datetime.combine(send_date, time(9, 0))
    send_time_tz = customer_tz.localize(send_time_local)
    send_time_utc = send_time_tz.astimezone(tz('UTC'))
    # Store send_time_utc in database
```

### Payment Idempotency
```python
idempotency_key = f"stripe_{transaction_id}_{amount}_{timestamp}"

# Check: exists?
existing = db.query(Payment).filter(
    Payment.idempotency_key == idempotency_key
).first()

if existing:
    return existing  # No duplicate

# Insert: new payment
payment = Payment(
    invoice_id=invoice_id,
    amount=amount,
    idempotency_key=idempotency_key,
    # ... other fields
)
db.add(payment)
db.commit()  # Transaction handles atomicity
return payment
```

---

## TESTING STRATEGY

### Unit Tests (70% of tests)
- **Customer Service:** 12 tests
- **Invoice Service:** 25 tests
- **Tax Calculation:** 15 tests
- **Payment Service:** 20 tests
- **Reminder Service:** 18 tests
- **Scheduler:** 12 tests
- **Audit Logging:** 10 tests
- **Total:** ~112 unit tests

### Integration Tests (25% of tests)
- **API Workflows:** 15 tests (full CRUD cycles)
- **Database Transactions:** 12 tests (ACID, rollback)
- **Concurrency:** 12 tests (race conditions)
- **Scheduler Integration:** 10 tests (job execution)
- **Webhook Simulation:** 8 tests (payment gateway)
- **Total:** ~57 integration tests

### Total Tests: **~170 tests**

### Coverage Target
- Overall: 85%+
- Financial calculations: 100%
- Critical paths: 100%
- Branches: High (80%+)

**Command:**
```bash
pytest -v --cov=app --cov-report=html
# Open htmlcov/index.html to view coverage
```

---

## DEPLOYMENT CHECKLIST

Before going to production:

**Code Quality**
- [ ] All tests passing: `pytest` (170/170)
- [ ] Code coverage ≥ 85%: `pytest --cov=app`
- [ ] No linting errors: `flake8 app/`
- [ ] Code formatted: `black app/`
- [ ] Security scan passed: `bandit -r app/`

**Database**
- [ ] Schema created and migrations run
- [ ] Audit log immutability verified (no DELETE allowed)
- [ ] Backups tested (restore and verify)
- [ ] Indexes created and performance verified

**Monitoring**
- [ ] CloudWatch/DataDog configured
- [ ] Alerts set up (error rate, latency, queue depth)
- [ ] Dashboards created
- [ ] Runbooks written

**Security**
- [ ] Secrets rotated (API keys, DB password, SMTP)
- [ ] TLS enabled (HTTPS everywhere)
- [ ] Rate limiting configured
- [ ] Authentication working (OAuth 2.0)

**Operations**
- [ ] Team trained on system
- [ ] Rollback plan documented
- [ ] Maintenance windows scheduled
- [ ] On-call rotation established

---

## SUCCESS METRICS (End of Week 5)

| Metric | Target | How to Verify |
|--------|--------|--------------|
| **Financial Accuracy** | 100% exact to cent | Compare 100 invoices to TaxJar API |
| **Reminder Idempotency** | 0 duplicate reminders | Run concurrent tests 100x; check no dups |
| **Payment Idempotency** | 0 duplicate payments | Send same webhook 10x; 1 payment created |
| **Scheduler Resilience** | 0 lost reminders | Kill scheduler; restart; verify all pending sent |
| **API Latency p95** | <300ms | Load test 100 concurrent users |
| **Scheduler Throughput** | 1000 reminders/sec | Measure send time for 10k reminders |
| **Code Coverage** | ≥85% | Run pytest --cov |
| **Test Pass Rate** | 100% | `pytest` — all 170 pass |
| **Security Issues** | 0 critical | Bandit scan; manual review |
| **Audit Trail** | Immutable | Verify no UPDATE/DELETE on audit_log |

---

## WHAT SUCCESS LOOKS LIKE

After 5 weeks of focused development:

✅ **System is production-ready** — Can handle real invoices, real payments, real reminders  
✅ **Correctness is guaranteed** — Financial calculations verified; audit trail complete  
✅ **Reliability is proven** — Tested under concurrency, failures, edge cases  
✅ **Team understands the code** — Clear patterns, comprehensive tests, good documentation  
✅ **Onboarding is easy** — New team members can understand and modify code within 1 day  
✅ **Operational runbooks exist** — How to monitor, debug, scale, respond to incidents  

---

## NEXT STEPS

1. **Today:** Read Sections 1–5 of OpenSpec (2 hours)
2. **Tomorrow:** Answer 10 open questions (1 hour); get stakeholder buy-in
3. **This week:** Set up development environment; review database schema
4. **Next week:** Start Phase 1 — begin customer management (Section 1.1 of Implementation-Kickoff-Guide)

---

## SUPPORT & QUESTIONS

**Before you ask:** Check Quick-Reference-Card.md (debugging, formulas, SQL snippets)  
**Still stuck?** Review the section of OpenSpec related to your question  
**Architecture question?** Check Architecture-Decisions.md (ADRs explain the reasoning)

---

## FINAL THOUGHTS

> *"The focus of this project is correctness, reliability, idempotency, and time-based workflows rather than UI complexity."*

This specification is **not about doing many things.** It's about **doing a few things perfectly.**

- No duplicate reminders
- No lost reminders
- No wrong tax calculations
- No inconsistent state under concurrency
- Full audit trail

That's it. That's the bar. Everything else is nice-to-have.

The test suite (170 tests) is your guarantee. If all tests pass, the system is correct.

---

**Status:** Specification COMPLETE and REVIEWED  
**Ready for:** Implementation by small, focused team (2–4 engineers)  
**Timeline:** 5 weeks to production-ready MVP  
**Next Milestone:** Phase 1 completion (Day 14)

---

**Questions?** Refer to the appropriate section of the OpenSpec. If it's not there, it's an open question — document it and add to Section 14.

Good luck! 🚀

---

**Version:** 1.0 | **Last Updated:** July 2026 | **Status:** READY FOR IMPLEMENTATION
