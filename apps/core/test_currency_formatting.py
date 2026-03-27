from decimal import Decimal

from apps.core.templatetags.currency import inr


def test_inr_filter_formats_values_with_indian_grouping():
    assert inr(Decimal("2499.50")) == "₹2,499.50"
    assert inr(Decimal("125000.00")) == "₹1,25,000.00"
    assert inr(Decimal("0")) == "₹0.00"


def test_inr_filter_handles_negative_and_invalid_values():
    assert inr(Decimal("-1499.5")) == "-₹1,499.50"
    assert inr("not-a-number") == "₹0.00"


