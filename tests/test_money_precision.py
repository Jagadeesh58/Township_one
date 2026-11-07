"""
Township One - Financial Precision and Money Rounding Verification Tests.

Test suite verifying:
- Authoritative exact decimal representations (Decimal and *_inr strings)
- Rounding behavior using ROUND_HALF_UP
- Immunity from binary floating point errors (e.g. 0.1 + 0.2 != 0.3)
- Multi-bill summation and balance integrity
- Precision across boundary values: ₹0.01, ₹0.10, ₹999.99, ₹1,000.00
"""

from decimal import Decimal, ROUND_HALF_UP
import pytest
from backend.app.services.billing import round_currency, calculate_principal, calculate_demo_late_fee


def test_round_currency_half_up_rules():
    """Verify half-up rounding (banker's / commercial standard) is consistently applied."""
    # Standard half up
    assert round_currency(Decimal("10.005")) == Decimal("10.01")
    assert round_currency(Decimal("10.004")) == Decimal("10.00")
    assert round_currency(Decimal("10.0051")) == Decimal("10.01")
    assert round_currency(Decimal("0.001")) == Decimal("0.00")
    assert round_currency(Decimal("0.005")) == Decimal("0.01")


def test_binary_float_immunity():
    """Verify Decimal arithmetic avoids the classic binary floating point representation defect."""
    # Classic floating point bug in Python: 0.1 + 0.2 = 0.30000000000000004
    float_sum = 0.1 + 0.2
    assert float_sum != 0.3

    # Decimal arithmetic is strictly exact
    decimal_sum = Decimal("0.10") + Decimal("0.20")
    assert decimal_sum == Decimal("0.30")
    assert round_currency(decimal_sum) == Decimal("0.30")


def test_boundary_values_and_formatting():
    """Verify formatting across boundary amounts."""
    amounts = [
        (Decimal("0.01"), "0.01"),
        (Decimal("0.10"), "0.10"),
        (Decimal("1.00"), "1.00"),
        (Decimal("999.99"), "999.99"),
        (Decimal("1000.00"), "1000.00"),
        (Decimal("10660.00"), "10660.00"),
    ]
    for dec_val, expected_str in amounts:
        rounded = round_currency(dec_val)
        assert f"{rounded:.2f}" == expected_str


def test_multi_bill_summation_precision():
    """Verify cumulative addition of fractional bills preserves exact penny balance."""
    # 100 bills of 63.705 (each rounds to 63.71)
    individual_rounded = [round_currency(Decimal("63.705")) for _ in range(100)]
    assert all(r == Decimal("63.71") for r in individual_rounded)
    total = sum(individual_rounded)
    assert total == Decimal("6371.00")


def test_area_rate_multiplication_precision():
    """Verify area (sq ft) multiplied by rate (INR/sq ft) always produces exact 2-decimal Decimal."""
    assert calculate_principal(Decimal("1150.00"), Decimal("6.50")) == Decimal("7475.00")
    assert calculate_principal(Decimal("980.00"), Decimal("6.50")) == Decimal("6370.00")
    assert calculate_principal(Decimal("1640.00"), Decimal("6.50")) == Decimal("10660.00")
    # Fractional square footage test
    assert calculate_principal(Decimal("1000.25"), Decimal("6.50")) == Decimal("6501.63")
