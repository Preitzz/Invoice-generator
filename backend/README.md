# Invoice Generator with Payment-Reminder Engine — Backend

FastAPI + SQLAlchemy 2.x + Alembic + PostgreSQL + Celery/Redis backend implementing
`openspec/changes/add-invoice-reminder-v1/implementation-plan.md`.

## Local dev environment

Preferred: `docker compose up -d` (Postgres 16 + Redis 7, see `docker-compose.yml`).

> **Sandbox note**: in the environment this backend was originally built in, outbound
> Docker Hub / registry image pulls were blocked by the network proxy (`docker pull
> postgres:16` returned `403 Forbidden`), so natively-installed `postgresql-16` and
> `redis-server` packages were used instead of containers for all development and test
> runs. `docker-compose.yml` is provided and known-correct for environments with normal
> registry access; nothing in the application code depends on which option you use.

Native fallback used in that environment:
```bash
service postgresql start
redis-server --daemonize yes --port 6379
# one-time role/db setup (idempotent):
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';"
sudo -u postgres psql -c "CREATE ROLE app_user LOGIN PASSWORD 'app_password';"
sudo -u postgres psql -c "CREATE DATABASE invoice_reminder OWNER postgres;"
sudo -u postgres psql -d invoice_reminder -c "GRANT ALL ON SCHEMA public TO app_user; GRANT CONNECT ON DATABASE invoice_reminder TO app_user;"
```

## Setup

```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # edit as needed
alembic upgrade head
python -m seed.seed_dev
```

## Running

```bash
uvicorn app.main:app --reload
celery -A app.tasks.celery_app worker -l info
celery -A app.tasks.celery_app beat -l info
```

## Tests

```bash
pytest tests/
```

Integration/e2e tests run against a real Postgres database (set `TEST_DATABASE_URL` or
rely on the default `invoice_reminder_test` database created by `tests/conftest.py`) —
they are not mocked, since several guarantees (audit-log grant revocation, `FOR UPDATE
SKIP LOCKED` claim semantics, `NUMERIC`/`JSONB`/enum behavior) are genuine Postgres
semantics that SQLite cannot reproduce.
