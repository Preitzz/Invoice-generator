from fastapi import APIRouter

from app.api.v1 import (
    audit_log,
    auth,
    customers,
    dashboard,
    invoices,
    payments,
    reminders,
    reports,
    system,
    tax_rates,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(customers.router)
api_router.include_router(invoices.router)
api_router.include_router(payments.router)
api_router.include_router(reminders.router)
api_router.include_router(tax_rates.router)
api_router.include_router(system.router)
api_router.include_router(audit_log.router)
api_router.include_router(dashboard.router)
api_router.include_router(reports.router)
