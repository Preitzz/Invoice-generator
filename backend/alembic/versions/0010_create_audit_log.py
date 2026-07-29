"""create audit_log table + revoke UPDATE/DELETE from app runtime role

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-29

This migration is the actual v1 enforcement mechanism for audit-log
append-only-ness (see openspec specs/audit-logging/spec.md): the application's
runtime DB role (`settings.APP_DB_ROLE`, default `app_user`) is granted only
INSERT/SELECT on this table, never UPDATE/DELETE. Migrations themselves run as
the DB owner/admin role (see alembic/env.py) and can still alter the table
schema — that's expected and orthogonal to this runtime-role restriction.
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

from alembic import op
from app.config import settings

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

APP_DB_ROLE = settings.APP_DB_ROLE


def upgrade() -> None:
    op.create_table(
        "audit_log",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("actor_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("before_state", pg.JSONB(), nullable=True),
        sa.Column("after_state", pg.JSONB(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Append-only enforcement at the DB grant level.
    op.execute("REVOKE UPDATE, DELETE ON audit_log FROM PUBLIC;")
    op.execute(f'REVOKE UPDATE, DELETE ON audit_log FROM "{APP_DB_ROLE}";')
    op.execute(f'GRANT INSERT, SELECT ON audit_log TO "{APP_DB_ROLE}";')


def downgrade() -> None:
    op.drop_table("audit_log")
