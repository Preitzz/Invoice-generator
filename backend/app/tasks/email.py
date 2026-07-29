"""Thin wrapper over an email provider (SES-class), swappable via a simple
interface so tests never hit a real network.
"""

import logging

from app.config import settings

logger = logging.getLogger("app.tasks.email")


class EmailDeliveryError(Exception):
    """Raised when the provider fails to accept/send an email. Celery
    autoretries on this exception in tasks/reminder_dispatch.py."""


class EmailProvider:
    def send(self, *, to: str, subject: str, body: str) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class FakeEmailProvider(EmailProvider):
    """Default provider for dev/test — records sends in-memory, never
    touches the network. `force_fail_next` lets tests simulate transient
    provider failures for the retry-policy test."""

    def __init__(self) -> None:
        self.sent: list[dict] = []
        self.force_fail_count = 0

    def send(self, *, to: str, subject: str, body: str) -> None:
        # Admin alerts are never subject to the simulated failure count —
        # they're the notification of last resort after retries are
        # exhausted and must not themselves be flaky in tests.
        if to != "admin-alerts@example.com" and self.force_fail_count > 0:
            self.force_fail_count -= 1
            raise EmailDeliveryError("Simulated transient provider failure")
        self.sent.append({"to": to, "subject": subject, "body": body})


_provider: EmailProvider = FakeEmailProvider()


def get_provider() -> EmailProvider:
    return _provider


def set_provider(provider: EmailProvider) -> None:
    global _provider
    _provider = provider


def send_reminder_email(instance, invoice) -> None:
    provider = get_provider()
    subject = f"Payment reminder for invoice {invoice.invoice_number or invoice.id}"
    body = (
        f"Dear {invoice.customer_name_snapshot},\n\n"
        f"This is a reminder regarding invoice {invoice.invoice_number} "
        f"for {invoice.total_amount} due on {invoice.due_date}.\n\n"
        f"Outstanding balance: {invoice.total_amount - invoice.amount_paid}."
    )
    provider.send(to=invoice.customer_email_snapshot, subject=subject, body=body)


def send_invoice_email(invoice) -> None:
    provider = get_provider()
    subject = f"Invoice {invoice.invoice_number} from our company"
    body = f"Please find attached invoice {invoice.invoice_number} for {invoice.total_amount}."
    provider.send(to=invoice.customer_email_snapshot, subject=subject, body=body)


def send_admin_alert(instance) -> None:
    provider = get_provider()
    provider.send(
        to="admin-alerts@example.com",
        subject="Reminder delivery permanently failed",
        body=f"Reminder instance {instance.id} for invoice {instance.invoice_id} failed after all retries.",
    )
