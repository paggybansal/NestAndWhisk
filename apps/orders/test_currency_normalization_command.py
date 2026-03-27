from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command

from apps.orders.models import Order, Payment


def _create_order_with_payment(*, order_currency: str, payment_currency: str) -> tuple[Order, Payment]:
    order = Order.objects.create(
        customer_email="guest@example.com",
        customer_first_name="Nest",
        customer_last_name="Guest",
        shipping_address_line_1="123 Baker Street",
        shipping_city="Delhi",
        shipping_state="Delhi",
        shipping_postal_code="110001",
        shipping_country="India",
        subtotal=Decimal("2499.50"),
        total=Decimal("2499.50"),
        currency=order_currency,
    )
    payment = Payment.objects.create(
        order=order,
        amount=Decimal("2499.50"),
        currency=payment_currency,
        status=Payment.Status.PENDING,
    )
    return order, payment


@pytest.mark.django_db
def test_normalize_order_payment_currency_dry_run_leaves_rows_unchanged():
    order, payment = _create_order_with_payment(order_currency="USD", payment_currency="usd")
    stdout = StringIO()

    call_command("normalize_order_payment_currency", "--dry-run", stdout=stdout)

    order.refresh_from_db()
    payment.refresh_from_db()

    assert order.currency == "USD"
    assert payment.currency == "usd"
    output = stdout.getvalue()
    assert "Orders needing normalization: 1" in output
    assert "Payments needing normalization: 1" in output
    assert "Dry run only. No database rows were changed." in output


@pytest.mark.django_db
def test_normalize_order_payment_currency_updates_legacy_rows_to_exact_inr():
    order, payment = _create_order_with_payment(order_currency="USD", payment_currency="usd")
    normalized_order, normalized_payment = _create_order_with_payment(order_currency="inr", payment_currency="inr")
    stdout = StringIO()

    call_command("normalize_order_payment_currency", stdout=stdout)

    order.refresh_from_db()
    payment.refresh_from_db()
    normalized_order.refresh_from_db()
    normalized_payment.refresh_from_db()

    assert order.currency == "INR"
    assert payment.currency == "INR"
    assert normalized_order.currency == "INR"
    assert normalized_payment.currency == "INR"
    output = stdout.getvalue()
    assert "Updated orders: 2" in output
    assert "Updated payments: 2" in output
    assert "Remaining non-INR orders: 0" in output
    assert "Remaining non-INR payments: 0" in output
    assert "Payment/order currency mismatches: 0" in output

