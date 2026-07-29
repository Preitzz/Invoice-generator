"""revoke DELETE on invoices/payments from app runtime role

Revision ID: 0014
Revises: 0013
Create Date: 2026-07-29

QA gap fix: the 7-year retention requirement in
openspec/changes/add-invoice-reminder-v1/specs/audit-logging/spec.md ("The
system SHALL retain invoices, payments, and audit log entries for a minimum
of 7 years ... and SHALL NOT provide any mechanism to purge or hard-delete
these records before that retention period elapses") was only enforced at
the DB grant level for audit_log (see 0010_create_audit_log.py). invoices
still granted full DELETE to the application's runtime DB role
(`settings.APP_DB_ROLE`) — no API endpoint happens to expose a delete route
today, but that was incidental safety only, not an enforced guard.

This migration revokes DELETE (and, for defense-in-depth, from PUBLIC) on
invoices and payments — matching the audit_log pattern and the exact set of
record types the spec names for 7-year retention. payments already only
grants SELECT/INSERT (see 0007_create_payments.py), so this is a no-op
there, included purely for consistency/explicitness.

invoice_line_items is deliberately NOT included here even though the earlier
QA note flagged it: the spec's retention requirement text names only
invoices, payments, and audit log entries as the retained record types, and
`app/services/invoices.py::update_invoice` legitimately deletes and
recreates a draft invoice's line items in place when its line items are
edited (a normal, spec-required update path, not a purge of a retained
financial record — the parent invoice row itself, which carries the
retained totals/history, is never deleted). Revoking DELETE on
invoice_line_items breaks that legitimate flow with a Postgres permission
error (confirmed via the full test suite — see
test_invoice_lifecycle.py::test_draft_edit_then_issue_recomputes_totals).

UPDATE is intentionally left untouched on invoices — editing pre-full-payment
is a legitimate, spec-required operation, distinct from hard-delete.
"""

import sqlalchemy as sa  # noqa: F401

from alembic import op
from app.config import settings

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None

APP_DB_ROLE = settings.APP_DB_ROLE

TABLES = ("invoices", "payments")


def upgrade() -> None:
    for table in TABLES:
        op.execute(f"REVOKE DELETE ON {table} FROM PUBLIC;")
        op.execute(f'REVOKE DELETE ON {table} FROM "{APP_DB_ROLE}";')


def downgrade() -> None:
    for table in TABLES:
        op.execute(f'GRANT DELETE ON {table} TO "{APP_DB_ROLE}";')
