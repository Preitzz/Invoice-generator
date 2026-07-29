"""create users table

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-29
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

from alembic import op
from app.config import settings

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

user_role = pg.ENUM("admin", "finance_staff", "viewer", name="user_role")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("role", user_role, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.execute(f'GRANT SELECT, INSERT, UPDATE, DELETE ON users TO "{settings.APP_DB_ROLE}";')


def downgrade() -> None:
    op.drop_table("users")
    user_role.drop(op.get_bind(), checkfirst=True)
