from decimal import Decimal
from html import unescape

import pytest
from django.urls import reverse

from apps.orders.models import Order, Payment


def _create_order_with_payment(*, total: str, currency: str = "USD") -> Order:
    order = Order.objects.create(
        customer_email="guest@example.com",
        customer_first_name="Nest",
        customer_last_name="Guest",
        shipping_address_line_1="123 Baker Street",
        shipping_city="Delhi",
        shipping_state="Delhi",
        shipping_postal_code="110001",
        shipping_country="India",
        subtotal=Decimal(total),
        total=Decimal(total),
        currency=currency,
    )
    Payment.objects.create(
        order=order,
        amount=Decimal(total),
        currency=currency,
        status=Payment.Status.PENDING,
    )
    return order


@pytest.mark.django_db
def test_checkout_success_renders_tracked_amount_without_legacy_currency_code(client):
    order = _create_order_with_payment(total="2499.50", currency="USD")

    response = client.get(reverse("checkout:success", kwargs={"order_number": order.order_number}))
    content = unescape(response.content.decode())

    assert response.status_code == 200
    assert "Care & gifting notes" in content
    assert "In this order" in content
    assert "Tracked amount" in content
    assert "₹2,499.50" in content
    assert "USD" not in content


@pytest.mark.django_db
def test_order_tracking_renders_total_with_inr_grouping(client):
    order = _create_order_with_payment(total="125000.00", currency="USD")

    response = client.get(reverse("checkout:tracking", kwargs={"order_number": order.order_number}))
    content = unescape(response.content.decode())

    assert response.status_code == 200
    assert "White-glove updates" in content
    assert "A clearer look at where the order stands." in content
    assert "₹1,25,000.00" in content
    assert "USD" not in content

