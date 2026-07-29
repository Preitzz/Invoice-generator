"""factory_boy factories mirroring seed/seed_dev.py's shapes at test scale."""

from datetime import date, timedelta
from decimal import Decimal

import factory

from app.core.security import hash_password
from app.models.customer import Customer
from app.models.payment import PaymentMethod
from app.models.tax_rate import TaxRate
from app.models.user import User, UserRole


class UserFactory(factory.Factory):
    class Meta:
        model = User

    name = factory.Faker("name")
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    role = UserRole.finance_staff
    password_hash = factory.LazyFunction(lambda: hash_password("TestPass123!"))
    is_active = True


class CustomerFactory(factory.Factory):
    class Meta:
        model = Customer

    name = factory.Faker("company")
    email = factory.Faker("company_email")
    phone = factory.Faker("numerify", text="##########")
    billing_address = factory.Faker("address")
    is_active = True


class TaxRateFactory(factory.Factory):
    class Meta:
        model = TaxRate

    name = "Standard Flat Rate"
    rate_percent = Decimal("18.00")
    effective_from = factory.LazyFunction(date.today)
    effective_to = None
    is_active = True


def make_line_item(description="Widget", quantity="1.00", unit_price="100.00"):
    return {"description": description, "quantity": quantity, "unit_price": unit_price}


def due_date_in(days: int) -> date:
    return date.today() + timedelta(days=days)


PAYMENT_METHODS = list(PaymentMethod)
