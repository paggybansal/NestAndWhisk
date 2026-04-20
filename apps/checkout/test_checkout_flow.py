from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory, override_settings
from django.urls import reverse

from apps.cart.models import Cart, CartItem
from apps.cart.services import get_or_create_cart
from apps.checkout.services import apply_mock_payment_outcome, create_stripe_checkout_session
from apps.catalog.models import Product, ProductCategory, ProductVariant
from apps.orders.models import Payment
from apps.orders.services import create_order_from_cart


def _create_product_with_variant():
    category = ProductCategory.objects.create(name="Gift Boxes", slug="gift-boxes")
    product = Product.objects.create(
        category=category,
        name="Signature Cookie Box",
        slug="signature-cookie-box",
        short_description="A curated cookie assortment.",
        description="A curated cookie assortment for gifting and everyday indulgence.",
    )
    variant = ProductVariant.objects.create(
        product=product,
        name="Box of 6",
        sku="NW-BOX-6",
        pack_size=6,
        price=Decimal("2499.50"),
        inventory_quantity=12,
    )
    return product, variant


def _checkout_payload():
    return {
        "customer_email": "guest@example.com",
        "customer_first_name": "Nest",
        "customer_last_name": "Guest",
        "customer_phone": "9999999999",
        "shipping_address_line_1": "123 Baker Street",
        "shipping_address_line_2": "",
        "shipping_city": "Delhi",
        "shipping_state": "Delhi",
        "shipping_postal_code": "110001",
        "shipping_country": "India",
        "delivery_notes": "",
        "payment_provider": "stripe",
        "payment_preference": "upi",
    }


@pytest.mark.django_db
@pytest.mark.parametrize("authenticated", [False, True])
def test_create_order_from_cart_deactivates_checked_out_cart_and_allows_fresh_active_cart(authenticated):
    product, variant = _create_product_with_variant()
    user = None
    session_key = "checkout-session-key"
    if authenticated:
        user = get_user_model().objects.create_user(email="buyer@example.com", password="testpass123")

    cart = Cart.objects.create(user=user, session_key=session_key, is_active=True)
    CartItem.objects.create(
        cart=cart,
        product=product,
        variant=variant,
        quantity=2,
        unit_price=variant.price,
    )

    order = create_order_from_cart(cart=cart, checkout_data=_checkout_payload(), user=user)

    cart.refresh_from_db()
    assert cart.is_active is False
    assert order.cart_id == cart.id
    assert order.items.count() == 1
    assert order.payments.count() == 1
    assert order.payments.first().provider == "stripe"
    assert order.payments.first().raw_response["checkout_preferences"]["payment_preference"] == "upi"
    assert order.payments.first().raw_response["checkout_preferences"]["payment_provider"] == "stripe"

    fresh_cart = get_or_create_cart(user=user, session_key=session_key)
    assert fresh_cart.id != cart.id
    assert fresh_cart.is_active is True
    assert fresh_cart.item_count == 0
    assert fresh_cart.items.count() == 0


@pytest.mark.django_db
@override_settings(STRIPE_SECRET_KEY="sk_test_example", STRIPE_ENABLE_UPI=True, STRIPE_CURRENCY="inr")
def test_create_stripe_checkout_session_includes_upi_for_inr_orders(monkeypatch):
    product, variant = _create_product_with_variant()
    cart = Cart.objects.create(session_key="upi-session", is_active=True)
    CartItem.objects.create(
        cart=cart,
        product=product,
        variant=variant,
        quantity=1,
        unit_price=variant.price,
    )
    order = create_order_from_cart(cart=cart, checkout_data=_checkout_payload(), user=None)
    payment = order.payments.first()
    factory = RequestFactory()
    request = factory.get("/checkout/", HTTP_HOST="127.0.0.1:8000")

    captured = {}

    class FakeSession:
        id = "cs_test_upi"
        payment_intent = "pi_test_upi"
        client_reference_id = ""
        url = "https://checkout.stripe.test/session"

        def to_dict_recursive(self):
            return {"id": self.id, "payment_intent": self.payment_intent, "url": self.url}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return FakeSession()

    monkeypatch.setattr("apps.checkout.services.stripe.checkout.Session.create", fake_create)

    checkout_url = create_stripe_checkout_session(order=order, payment=payment, request=request)
    payment.refresh_from_db()

    assert checkout_url == "https://checkout.stripe.test/session"
    assert captured["payment_method_types"] == ["upi", "card"]
    assert captured["metadata"]["payment_provider"] == "stripe"
    assert captured["metadata"]["payment_preference"] == "upi"
    assert payment.raw_response["checkout_preferences"]["payment_method_types"] == ["upi", "card"]
    assert payment.raw_response["checkout_preferences"]["payment_provider"] == "stripe"
    assert payment.status == Payment.Status.REQUIRES_ACTION


@pytest.mark.django_db
@override_settings(MOCK_PAYMENT_ENABLED=True)
def test_create_order_from_cart_can_store_mock_payment_provider():
    product, variant = _create_product_with_variant()
    cart = Cart.objects.create(session_key="mock-provider-session", is_active=True)
    CartItem.objects.create(
        cart=cart,
        product=product,
        variant=variant,
        quantity=1,
        unit_price=variant.price,
    )
    payload = _checkout_payload() | {"payment_provider": "mock", "payment_preference": "flexible"}

    order = create_order_from_cart(cart=cart, checkout_data=payload, user=None)
    payment = order.payments.first()

    assert payment.provider == "mock"
    assert payment.raw_response["checkout_preferences"]["payment_provider"] == "mock"


@pytest.mark.django_db
@override_settings(MOCK_PAYMENT_ENABLED=True)
def test_mock_payment_simulator_marks_payment_paid(client):
    product, variant = _create_product_with_variant()
    cart = Cart.objects.create(session_key="mock-simulator-session", is_active=True)
    CartItem.objects.create(
        cart=cart,
        product=product,
        variant=variant,
        quantity=1,
        unit_price=variant.price,
    )
    order = create_order_from_cart(
        cart=cart,
        checkout_data=_checkout_payload() | {"payment_provider": "mock", "payment_preference": "flexible"},
        user=None,
    )

    response = client.post(reverse("checkout:mock_payment", kwargs={"order_number": order.order_number}), {"outcome": "success"}, follow=False)
    order.refresh_from_db()
    payment = order.payments.first()

    assert response.status_code == 302
    assert response["Location"] == reverse("checkout:success", kwargs={"order_number": order.order_number})
    assert order.payment_status == order.PaymentStatus.PAID
    assert order.status == order.Status.PAID
    assert payment.status == Payment.Status.SUCCEEDED


@pytest.mark.django_db
def test_apply_mock_payment_outcome_marks_failure_retryable():
    product, variant = _create_product_with_variant()
    cart = Cart.objects.create(session_key="mock-outcome-session", is_active=True)
    CartItem.objects.create(
        cart=cart,
        product=product,
        variant=variant,
        quantity=1,
        unit_price=variant.price,
    )
    order = create_order_from_cart(
        cart=cart,
        checkout_data=_checkout_payload() | {"payment_provider": "mock", "payment_preference": "flexible"},
        user=None,
    )
    payment = order.payments.first()

    apply_mock_payment_outcome(payment=payment, outcome="failed")
    order.refresh_from_db()
    payment.refresh_from_db()

    assert order.payment_status == order.PaymentStatus.FAILED
    assert payment.status == Payment.Status.FAILED


@pytest.mark.django_db
def test_checkout_invalid_post_shows_delhi_ncr_delivery_guidance_for_matching_address(client):
    product, variant = _create_product_with_variant()
    session = client.session
    session.save()
    cart = Cart.objects.create(session_key=session.session_key, is_active=True)
    CartItem.objects.create(
        cart=cart,
        product=product,
        variant=variant,
        quantity=1,
        unit_price=variant.price,
    )

    payload = _checkout_payload() | {"customer_email": "", "shipping_city": "Gurgaon", "shipping_postal_code": "122002"}
    response = client.post(reverse("checkout:index"), payload)
    content = response.content.decode()

    assert response.status_code == 200
    assert "This field is required." in content
    assert "Delhi NCR delivery only" in content
    assert "Please enter a valid Delhi NCR pincode." in content


