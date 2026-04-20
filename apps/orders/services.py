from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.cart.models import Cart
from apps.cart.services import deactivate_cart
from apps.orders.models import Order, OrderItem, Payment


def update_order_payment_state(*, order: Order, payment_status: str, status: str | None = None):
    order.payment_status = payment_status
    update_fields = ["payment_status", "updated_at"]
    if status is not None:
        order.status = status
        update_fields.append("status")
    order.save(update_fields=update_fields)


def mark_payment_processing(
    *,
    payment: Payment,
    checkout_id: str = "",
    payment_id: str = "",
    provider_reference: str = "",
    raw_response: dict | None = None,
):
    payment.provider_checkout_id = checkout_id or payment.provider_checkout_id
    payment.provider_payment_id = payment_id or payment.provider_payment_id
    payment.provider_reference = provider_reference or payment.provider_reference
    payment.status = Payment.Status.REQUIRES_ACTION
    if raw_response is not None:
        payment.raw_response = raw_response
    payment.save(
        update_fields=[
            "provider_checkout_id",
            "provider_payment_id",
            "provider_reference",
            "status",
            "raw_response",
            "updated_at",
        ]
    )
    order = payment.order
    order.provider = payment.provider
    order.provider_checkout_id = payment.provider_checkout_id
    order.provider_payment_id = payment.provider_payment_id
    order.save(
        update_fields=[
            "provider",
            "provider_checkout_id",
            "provider_payment_id",
            "updated_at",
        ]
    )
    update_order_payment_state(order=order, payment_status=Order.PaymentStatus.PROCESSING)


def mark_payment_succeeded(
    *,
    payment: Payment,
    provider_payment_id: str = "",
    provider_reference: str = "",
    receipt_url: str = "",
    raw_response: dict | None = None,
):
    payment.provider_payment_id = provider_payment_id or payment.provider_payment_id
    payment.provider_reference = provider_reference or payment.provider_reference
    payment.receipt_url = receipt_url or payment.receipt_url
    payment.status = Payment.Status.SUCCEEDED
    payment.paid_at = timezone.now()
    if raw_response is not None:
        payment.raw_response = raw_response
    payment.save(
        update_fields=[
            "provider_payment_id",
            "provider_reference",
            "receipt_url",
            "status",
            "paid_at",
            "raw_response",
            "updated_at",
        ]
    )
    order = payment.order
    order.provider_payment_id = payment.provider_payment_id
    order.save(update_fields=["provider_payment_id", "updated_at"])
    update_order_payment_state(
        order=order,
        payment_status=Order.PaymentStatus.PAID,
        status=Order.Status.PAID,
    )


def mark_payment_failed(
    *,
    payment: Payment,
    provider_reference: str = "",
    raw_response: dict | None = None,
):
    payment.provider_reference = provider_reference or payment.provider_reference
    payment.status = Payment.Status.FAILED
    if raw_response is not None:
        payment.raw_response = raw_response
    payment.save(update_fields=["provider_reference", "status", "raw_response", "updated_at"])
    update_order_payment_state(order=payment.order, payment_status=Order.PaymentStatus.FAILED)


def mark_payment_cancelled(
    *,
    payment: Payment,
    provider_reference: str = "",
    raw_response: dict | None = None,
):
    payment.provider_reference = provider_reference or payment.provider_reference
    payment.status = Payment.Status.CANCELLED
    if raw_response is not None:
        payment.raw_response = raw_response
    payment.save(update_fields=["provider_reference", "status", "raw_response", "updated_at"])
    update_order_payment_state(order=payment.order, payment_status=Order.PaymentStatus.UNPAID)


def mark_payment_refunded(
    *,
    payment: Payment,
    provider_reference: str = "",
    raw_response: dict | None = None,
):
    payment.provider_reference = provider_reference or payment.provider_reference
    payment.status = Payment.Status.REFUNDED
    if raw_response is not None:
        payment.raw_response = raw_response
    payment.save(update_fields=["provider_reference", "status", "raw_response", "updated_at"])
    update_order_payment_state(order=payment.order, payment_status=Order.PaymentStatus.REFUNDED)


def create_pending_payment_for_order(*, order: Order, provider: str = "stripe", metadata: dict | None = None) -> Payment:
    payment = Payment.objects.create(
        order=order,
        amount=order.total,
        currency=order.currency,
        provider=provider,
        status=Payment.Status.PENDING,
        raw_response=metadata or {},
    )
    order.provider = provider
    order.save(update_fields=["provider", "updated_at"])
    return payment


@transaction.atomic
def create_order_from_cart(*, cart: Cart, checkout_data: dict, user=None) -> Order:
    subtotal = cart.subtotal
    shipping_total = Decimal("0.00")
    discount_total = Decimal("0.00")
    currency = settings.STRIPE_CURRENCY.upper()
    order = Order.objects.create(
        user=user if getattr(user, "is_authenticated", False) else None,
        cart=cart,
        customer_email=checkout_data["customer_email"],
        customer_first_name=checkout_data["customer_first_name"],
        customer_last_name=checkout_data.get("customer_last_name", ""),
        customer_phone=checkout_data.get("customer_phone", ""),
        shipping_address_line_1=checkout_data["shipping_address_line_1"],
        shipping_address_line_2=checkout_data.get("shipping_address_line_2", ""),
        shipping_city=checkout_data["shipping_city"],
        shipping_state=checkout_data["shipping_state"],
        shipping_postal_code=checkout_data["shipping_postal_code"],
        shipping_country=checkout_data["shipping_country"],
        delivery_notes=checkout_data.get("delivery_notes", ""),
        preferred_delivery_date=cart.preferred_delivery_date,
        subtotal=subtotal,
        discount_total=discount_total,
        shipping_total=shipping_total,
        total=subtotal - discount_total + shipping_total,
        currency=currency,
        placed_at=timezone.now(),
    )

    for cart_item in cart.items.select_related("product", "variant"):
        OrderItem.objects.create(
            order=order,
            product=cart_item.product,
            variant=cart_item.variant,
            product_name=cart_item.product.name,
            variant_name=cart_item.variant.name if cart_item.variant else "",
            sku=cart_item.variant.sku if cart_item.variant else "",
            quantity=cart_item.quantity,
            unit_price=cart_item.unit_price,
            line_total=cart_item.line_total,
        )

    create_pending_payment_for_order(
        order=order,
        provider=checkout_data.get("payment_provider", "offline"),
        metadata={
            "checkout_preferences": {
                "payment_option": checkout_data.get("payment_option", "online_link"),
                "payment_provider": checkout_data.get("payment_provider", "offline"),
                "payment_preference": checkout_data.get("payment_preference", "flexible"),
                "currency": currency,
            }
        },
    )
    deactivate_cart(cart=cart)
    return order
