"""Domain exception classes and FastAPI exception handlers.

Each domain exception maps to a specific HTTP status code so that service-layer
code can raise semantically meaningful errors without importing FastAPI/HTTP
concerns directly.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class DomainError(Exception):
    """Base class for all business-rule violations raised from services/."""

    status_code = status.HTTP_400_BAD_REQUEST
    code = "domain_error"

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class NotFoundError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class OverpaymentError(DomainError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "overpayment"


class EditBelowPaymentsError(DomainError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "edit_below_payments"


class InvoiceNotEditableError(DomainError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "invoice_not_editable"


class CancelWithPaymentsError(DomainError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "cancel_with_payments"


class CustomerHasOpenInvoicesError(DomainError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "customer_has_open_invoices"


class DuplicatePaymentWarning(DomainError):
    """Not a hard error — surfaced as a 409 requiring confirmation."""

    status_code = status.HTTP_409_CONFLICT
    code = "duplicate_payment_warning"


class InvalidStateTransitionError(DomainError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "invalid_state_transition"


class AuthenticationError(DomainError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "authentication_error"


class AuthorizationError(DomainError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "authorization_error"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message, "code": exc.code},
        )
