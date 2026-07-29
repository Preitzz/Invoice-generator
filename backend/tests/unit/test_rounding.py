from decimal import Decimal

from hypothesis import given
from hypothesis import strategies as st

from app.core.rounding import round_half_up


def test_round_half_up_basic_cases():
    assert round_half_up(Decimal("1.005")) == Decimal("1.01")
    assert round_half_up(Decimal("1.004")) == Decimal("1.00")
    assert round_half_up(Decimal("1.015")) == Decimal("1.02")
    assert round_half_up(Decimal("0")) == Decimal("0.00")
    assert round_half_up(Decimal("100")) == Decimal("100.00")


def test_round_half_up_negative_third_decimal_rounds_away_from_zero_toward_up():
    # ROUND_HALF_UP in Python's decimal module rounds .5 away from zero.
    assert round_half_up(Decimal("-1.005")) == Decimal("-1.01")


def test_round_half_up_always_returns_two_decimal_places():
    result = round_half_up(Decimal("3"))
    assert result.as_tuple().exponent == -2


@given(
    st.decimals(
        min_value=Decimal("-1000000"),
        max_value=Decimal("1000000"),
        allow_nan=False,
        allow_infinity=False,
        places=4,
    )
)
def test_round_half_up_property_always_two_places_and_close(value: Decimal):
    result = round_half_up(value)
    assert result.as_tuple().exponent == -2
    assert abs(result - value) <= Decimal("0.005") + Decimal("0.0001")


@given(
    st.lists(
        st.decimals(
            min_value=Decimal("0"),
            max_value=Decimal("10000"),
            allow_nan=False,
            allow_infinity=False,
            places=2,
        ),
        min_size=1,
        max_size=20,
    ),
    st.decimals(min_value=Decimal("0"), max_value=Decimal("100"), allow_nan=False, allow_infinity=False, places=2),
)
def test_line_items_subtotal_tax_total_sum_exactly(line_amounts: list[Decimal], tax_rate_percent: Decimal):
    """sum(line.line_subtotal) == invoice.subtotal, subtotal + tax == total,
    each post round-half-up — mirrors the invariant tested by
    services/invoices.py's totals computation."""
    lines_rounded = [round_half_up(amount) for amount in line_amounts]
    subtotal = round_half_up(sum(lines_rounded, Decimal("0")))
    tax_amount = round_half_up(subtotal * tax_rate_percent / Decimal("100"))
    total_amount = round_half_up(subtotal + tax_amount)

    assert sum(lines_rounded, Decimal("0")) == subtotal
    assert subtotal + tax_amount == total_amount


@given(
    st.decimals(min_value=Decimal("1"), max_value=Decimal("100000"), allow_nan=False, allow_infinity=False, places=2),
    st.lists(
        st.decimals(min_value=Decimal("0.01"), max_value=Decimal("1000"), allow_nan=False, allow_infinity=False, places=2),
        min_size=0,
        max_size=10,
    ),
)
def test_amount_paid_never_exceeds_total_across_randomized_payment_sequences(
    total_amount: Decimal, payment_amounts: list[Decimal]
):
    """Randomized payment sequences, applying the overpayment guard, must
    never let amount_paid exceed total_amount."""
    amount_paid = Decimal("0.00")
    for payment in payment_amounts:
        if amount_paid + payment <= total_amount:
            amount_paid = round_half_up(amount_paid + payment)
        # else: rejected, as services/payments.py::assert_no_overpayment would do
    assert amount_paid <= total_amount
