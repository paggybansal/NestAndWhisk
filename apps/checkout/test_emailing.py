import pytest
from django.core import mail
from html import unescape

from apps.checkout.emailing import send_tracking_links_email_for_order
from apps.core.branding import get_brand_logo_path
from apps.orders.models import Order


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("tracking_url", "success_url"),
    [
        (
            "http://127.0.0.1:8000/checkout/track/NWTEST123456/",
            "http://127.0.0.1:8000/checkout/success/NWTEST123456/",
        )
    ],
)
def test_tracking_email_uses_branded_logo_html_template(settings, tracking_url, success_url):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

    order = Order.objects.create(
        customer_email="guest@example.com",
        customer_first_name="Nest",
        customer_last_name="Guest",
        shipping_address_line_1="123 Baker Street",
        shipping_city="Delhi",
        shipping_state="Delhi",
        shipping_postal_code="110001",
        shipping_country="India",
        subtotal="24.00",
        total="24.00",
    )

    send_tracking_links_email_for_order(
        order_id=order.pk,
        tracking_url=tracking_url,
        success_url=success_url,
    )

    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.subject == f"Your Nest & Whisk tracking links for {order.order_number}"
    assert message.to == [order.customer_email]
    assert len(message.alternatives) == 1

    html_body, mimetype = message.alternatives[0]
    html_body = unescape(html_body)
    expected_logo_url = f"http://127.0.0.1:8000{get_brand_logo_path()}"
    assert mimetype == "text/html"
    assert "Nest & Whisk" in html_body
    assert "Your order links are ready." in html_body
    assert expected_logo_url in html_body
    assert tracking_url in html_body
    assert success_url in html_body

