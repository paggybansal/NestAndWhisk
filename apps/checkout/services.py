from decimal import Decimal

from django.conf import settings
from django.urls import reverse
from django.utils import timezone

import stripe

from apps.orders.models import Order, Payment, PaymentEvent, PaymentWebhookEvent
from apps.orders.services import (
    mark_payment_cancelled,
    mark_payment_failed,
    mark_payment_processing,
    mark_payment_refunded,
    mark_payment_succeeded,
)


class StripeCheckoutConfigurationError(Exception):
    pass


class StripeWebhookConfigurationError(Exception):
    pass


class MockPaymentConfigurationError(Exception):
    pass


def _extract_receipt_url(data: dict) -> str:
    charges = data.get("charges", {}).get("data", [])
    return charges[0].get("receipt_url", "") if charges else ""


def _get_checkout_payment_preference(payment: Payment) -> str:
    return (
        payment.raw_response.get("checkout_preferences", {}).get("payment_preference", "flexible")
        if isinstance(payment.raw_response, dict)
        else "flexible"
    )


def get_stripe_payment_method_types(*, currency: str, payment_preference: str) -> list[str]:
    methods = ["card"]
    supports_upi = settings.STRIPE_ENABLE_UPI and currency.lower() == "inr"
    if supports_upi:
        methods.append("upi")

    if payment_preference == "upi" and supports_upi:
        return ["upi", "card"]
    return methods


def _record_payment_event(*, payment: Payment, event_type: str, data: dict, amount: Decimal | None = None):
    PaymentEvent.objects.create(
        payment=payment,
        event_type=event_type,
        provider_reference=data.get("id", "") or data.get("payment_intent", ""),
        amount=amount if amount is not None else payment.amount,
        currency=(data.get("currency") or payment.currency).upper(),
        payload=data,
        occurred_at=timezone.now(),
    )


def _get_or_create_webhook_event(*, event: dict) -> tuple[PaymentWebhookEvent, bool]:
    webhook_event, created = PaymentWebhookEvent.objects.get_or_create(
        event_id=event["id"],
        defaults={
            "provider": "stripe",
            "event_type": event["type"],
            "object_id": event["data"]["object"].get("id", ""),
            "payload": event,
        },
    )
    if not created:
        webhook_event.payload = event
        webhook_event.event_type = event["type"]
        webhook_event.object_id = event["data"]["object"].get("id", "")
        webhook_event.save(update_fields=["payload", "event_type", "object_id", "updated_at"])
    return webhook_event, created


def _finalize_webhook_event(*, webhook_event: PaymentWebhookEvent, payment: Payment | None = None, order: Order | None = None, note: str = ""):
    webhook_event.payment = payment
    webhook_event.order = order or (payment.order if payment else None)
    webhook_event.is_processed = True
    webhook_event.processed_at = timezone.now()
    webhook_event.processing_notes = note
    webhook_event.save(
        update_fields=[
            "payment",
            "order",
            "is_processed",
            "processed_at",
            "processing_notes",
            "updated_at",
        ]
    )


def create_stripe_checkout_session(*, order: Order, payment: Payment, request) -> str:
    if not settings.STRIPE_SECRET_KEY:
        raise StripeCheckoutConfigurationError("Stripe secret key is not configured.")

    stripe.api_key = settings.STRIPE_SECRET_KEY
    payment_preference = _get_checkout_payment_preference(payment)
    existing_checkout_preferences = (
        payment.raw_response.get("checkout_preferences", {})
        if isinstance(payment.raw_response, dict)
        else {}
    )
    payment_method_types = get_stripe_payment_method_types(
        currency=order.currency,
        payment_preference=payment_preference,
    )
    success_url = request.build_absolute_uri(
        reverse("checkout:success", kwargs={"order_number": order.order_number})
    )
    cancel_url = request.build_absolute_uri(
        reverse("checkout:cancelled", kwargs={"order_number": order.order_number})
    )

    session = stripe.checkout.Session.create(
        mode="payment",
        payment_method_types=payment_method_types,
        success_url=success_url,
        cancel_url=cancel_url,
        customer_email=order.customer_email,
        metadata={
            "order_number": order.order_number,
            "payment_id": str(payment.pk),
            "payment_provider": payment.provider,
            "payment_preference": payment_preference,
        },
        line_items=[
            {
                "price_data": {
                    "currency": settings.STRIPE_CURRENCY.lower(),
                    "product_data": {
                        "name": f"Nest & Whisk Order {order.order_number}",
                        "description": f"{order.items.count()} handcrafted line item(s)",
                    },
                    "unit_amount": int(order.total * 100),
                },
                "quantity": 1,
            }
        ],
    )

    mark_payment_processing(
        payment=payment,
        checkout_id=session.id,
        payment_id=session.payment_intent or "",
        provider_reference=session.client_reference_id or "",
        raw_response={
            **(payment.raw_response if isinstance(payment.raw_response, dict) else {}),
            "checkout_preferences": {
                **existing_checkout_preferences,
                "payment_preference": payment_preference,
                "payment_method_types": payment_method_types,
                "currency": order.currency,
                "upi_enabled": "upi" in payment_method_types,
            },
            "stripe_checkout_session": session.to_dict_recursive(),
        },
    )
    _record_payment_event(payment=payment, event_type="checkout.session.created", data=session.to_dict_recursive())

    return session.url


def construct_stripe_event(*, payload: bytes, signature: str):
    if not settings.STRIPE_SECRET_KEY or not settings.STRIPE_WEBHOOK_SECRET:
        raise StripeWebhookConfigurationError("Stripe webhook secret is not configured.")

    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe.Webhook.construct_event(payload, signature, settings.STRIPE_WEBHOOK_SECRET)


def handle_stripe_event(event):
    webhook_event, created = _get_or_create_webhook_event(event=event)
    if webhook_event.is_processed and not created:
        return

    event_type = event["type"]
    data = event["data"]["object"]
    payment = None

    if event_type in {"checkout.session.completed", "checkout.session.expired", "checkout.session.async_payment_succeeded", "checkout.session.async_payment_failed"}:
        payment = Payment.objects.filter(provider_checkout_id=data.get("id")).select_related("order").first()
    elif event_type in {"payment_intent.succeeded", "payment_intent.payment_failed", "charge.refunded", "refund.updated"}:
        payment = Payment.objects.filter(provider_payment_id=data.get("id") or data.get("payment_intent")).select_related("order").first()

    if event_type == "checkout.session.completed" and payment:
        mark_payment_succeeded(
            payment=payment,
            provider_payment_id=data.get("payment_intent", ""),
            provider_reference=data.get("payment_status", ""),
            receipt_url=data.get("url", ""),
            raw_response=data,
        )
        _record_payment_event(payment=payment, event_type=event_type, data=data)
        _finalize_webhook_event(webhook_event=webhook_event, payment=payment, note="checkout session completed")
        return

    if event_type in {"payment_intent.succeeded", "checkout.session.async_payment_succeeded"} and payment:
        mark_payment_succeeded(
            payment=payment,
            provider_payment_id=data.get("id", "") or data.get("payment_intent", ""),
            provider_reference=data.get("status", ""),
            receipt_url=_extract_receipt_url(data),
            raw_response=data,
        )
        _record_payment_event(payment=payment, event_type=event_type, data=data)
        _finalize_webhook_event(webhook_event=webhook_event, payment=payment, note="payment succeeded")
        return

    if event_type in {"payment_intent.payment_failed", "checkout.session.async_payment_failed"} and payment:
        mark_payment_failed(
            payment=payment,
            provider_reference=data.get("last_payment_error", {}).get("message", "") or data.get("status", ""),
            raw_response=data,
        )
        _record_payment_event(payment=payment, event_type=event_type, data=data)
        _finalize_webhook_event(webhook_event=webhook_event, payment=payment, note="payment failed")
        return

    if event_type == "checkout.session.expired" and payment:
        mark_payment_cancelled(
            payment=payment,
            provider_reference="expired",
            raw_response=data,
        )
        _record_payment_event(payment=payment, event_type=event_type, data=data)
        _finalize_webhook_event(webhook_event=webhook_event, payment=payment, note="checkout session expired")
        return

    if event_type in {"charge.refunded", "refund.updated"} and payment:
        refund_amount = Decimal(str((data.get("amount_refunded") or data.get("amount") or 0) / 100))
        mark_payment_refunded(
            payment=payment,
            provider_reference=data.get("id", "") or data.get("status", ""),
            raw_response=data,
        )
        _record_payment_event(payment=payment, event_type=event_type, data=data, amount=refund_amount)
        _finalize_webhook_event(webhook_event=webhook_event, payment=payment, note="refund recorded")
        return

    _finalize_webhook_event(webhook_event=webhook_event, payment=payment, note="event received without state transition")


def apply_mock_payment_outcome(*, payment: Payment, outcome: str):
    outcome_map = {
        "success": (mark_payment_succeeded, "mock.payment.succeeded", "mock_success"),
        "failed": (mark_payment_failed, "mock.payment.failed", "mock_failed"),
        "cancelled": (mark_payment_cancelled, "mock.payment.cancelled", "mock_cancelled"),
    }
    if outcome not in outcome_map:
        raise MockPaymentConfigurationError("Unsupported mock payment outcome.")

    transition, event_type, provider_reference = outcome_map[outcome]
    transition(
        payment=payment,
        provider_reference=provider_reference,
        raw_response={
            **(payment.raw_response if isinstance(payment.raw_response, dict) else {}),
            "mock_payment": {
                "outcome": outcome,
                "applied_at": timezone.now().isoformat(),
            },
        },
    )
    _record_payment_event(
        payment=payment,
        event_type=event_type,
        data={
            "id": provider_reference,
            "provider": "mock",
            "status": outcome,
        },
    )

