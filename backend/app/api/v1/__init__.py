from fastapi import APIRouter

api_router = APIRouter()

# Routers are registered incrementally as each phase implements them.
try:
    from app.api.v1 import auth

    api_router.include_router(auth.router)
except ImportError:
    pass

try:
    from app.api.v1 import customers

    api_router.include_router(customers.router)
except ImportError:
    pass

try:
    from app.api.v1 import invoices

    api_router.include_router(invoices.router)
except ImportError:
    pass

try:
    from app.api.v1 import payments

    api_router.include_router(payments.router)
except ImportError:
    pass

try:
    from app.api.v1 import tax_rates

    api_router.include_router(tax_rates.router)
except ImportError:
    pass

try:
    from app.api.v1 import reminders

    api_router.include_router(reminders.router)
except ImportError:
    pass

try:
    from app.api.v1 import system

    api_router.include_router(system.router)
except ImportError:
    pass

try:
    from app.api.v1 import audit_log

    api_router.include_router(audit_log.router)
except ImportError:
    pass

try:
    from app.api.v1 import dashboard

    api_router.include_router(dashboard.router)
except ImportError:
    pass

try:
    from app.api.v1 import reports

    api_router.include_router(reports.router)
except ImportError:
    pass
