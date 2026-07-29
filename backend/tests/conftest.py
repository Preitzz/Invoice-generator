import os
import uuid
from datetime import date
from decimal import Decimal

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session, sessionmaker

os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://app_user:app_password@localhost:5432/invoice_reminder_test"
)
os.environ.setdefault(
    "DATABASE_URL_SYNC_ADMIN",
    "postgresql+psycopg://postgres:postgres@localhost:5432/invoice_reminder_test",
)

from app.config import settings  # noqa: E402

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ADMIN_ROOT_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/postgres"
TEST_DB_NAME = "invoice_reminder_test"


def _ensure_test_database_exists() -> None:
    root_engine = sa.create_engine(ADMIN_ROOT_URL, isolation_level="AUTOCOMMIT")
    with root_engine.connect() as conn:
        exists = conn.execute(
            sa.text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": TEST_DB_NAME}
        ).scalar()
        if not exists:
            conn.execute(sa.text(f'CREATE DATABASE "{TEST_DB_NAME}" OWNER postgres'))
        conn.execute(
            sa.text(
                f'GRANT ALL ON SCHEMA public TO "{settings.APP_DB_ROLE}"; '
                f'GRANT CONNECT ON DATABASE "{TEST_DB_NAME}" TO "{settings.APP_DB_ROLE}";'
            )
        )
    root_engine.dispose()


def _run_migrations() -> None:
    alembic_cfg = Config(os.path.join(BACKEND_DIR, "alembic.ini"))
    alembic_cfg.set_main_option("script_location", os.path.join(BACKEND_DIR, "alembic"))
    command.downgrade(alembic_cfg, "base")
    command.upgrade(alembic_cfg, "head")


@pytest.fixture(scope="session", autouse=True)
def _test_database():
    _ensure_test_database_exists()
    _run_migrations()
    yield


@pytest.fixture(scope="session")
def engine(_test_database):
    eng = sa.create_engine(settings.DATABASE_URL, future=True)
    yield eng
    eng.dispose()


@pytest.fixture()
def db_session(engine) -> Session:
    connection = engine.connect()
    trans = connection.begin()
    SessionFactory = sessionmaker(bind=connection, future=True, expire_on_commit=False)
    session = SessionFactory()

    # Allow inner code to call session.commit() without ending the outer
    # transaction — nest via SAVEPOINT so every test still fully rolls back.
    nested = connection.begin_nested()

    @sa.event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess, trans_):
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()

    try:
        yield session
    finally:
        session.close()
        if trans.is_active:
            trans.rollback()
        connection.close()


@pytest.fixture()
def client(db_session):
    from fastapi.testclient import TestClient

    from app.api import deps
    from app.main import app

    def _get_db_override():
        yield db_session

    app.dependency_overrides[deps.get_db] = _get_db_override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Seeded fixtures used across unit + integration tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def admin_user(db_session):
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        name="Admin User",
        email=f"admin-{uuid.uuid4().hex[:8]}@example.com",
        role=UserRole.admin,
        password_hash=hash_password("AdminPass123!"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def finance_user(db_session):
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        name="Finance Staff",
        email=f"finance-{uuid.uuid4().hex[:8]}@example.com",
        role=UserRole.finance_staff,
        password_hash=hash_password("FinancePass123!"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def viewer_user(db_session):
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        name="Viewer",
        email=f"viewer-{uuid.uuid4().hex[:8]}@example.com",
        role=UserRole.viewer,
        password_hash=hash_password("ViewerPass123!"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def active_tax_rate(db_session):
    from app.models.tax_rate import TaxRate

    rate = db_session.query(TaxRate).filter(TaxRate.is_active.is_(True)).first()
    if rate is None:
        rate = TaxRate(
            name="Standard Flat Rate",
            rate_percent=Decimal("18.00"),
            effective_from=date.today(),
            is_active=True,
        )
        db_session.add(rate)
        db_session.commit()
        db_session.refresh(rate)
    return rate


@pytest.fixture()
def customer(db_session):
    from app.models.customer import Customer

    cust = Customer(
        name="Acme Corp",
        email="acme@example.com",
        phone="9999999999",
        billing_address="123 Business Rd, Bengaluru, KA",
        is_active=True,
    )
    db_session.add(cust)
    db_session.commit()
    db_session.refresh(cust)
    return cust
