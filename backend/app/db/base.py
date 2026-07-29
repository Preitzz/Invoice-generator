from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base. Import hub for all models below so that
    Alembic's env.py sees the full metadata for autogeneration."""


# Import hub — every model must be imported here so Base.metadata is complete.
from app.models import (  # noqa: E402,F401
    user,
    customer,
    tax_rate,
    invoice,
    invoice_line_item,
    payment,
    reminder_rule,
    reminder_instance,
    audit_log,
    system_settings,
)
