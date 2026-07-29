"""Fixed-point rounding helper — the single place every derived monetary
value in the system must pass through. Never use float for money.
"""

from decimal import ROUND_HALF_UP, Decimal

TWO_PLACES = Decimal("0.01")


def round_half_up(value: Decimal) -> Decimal:
    """Round a Decimal to 2 decimal places (nearest paisa) using round-half-up."""
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
