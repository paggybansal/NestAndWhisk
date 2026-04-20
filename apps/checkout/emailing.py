from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from urllib.parse import urlsplit
import logging

from apps.core.branding import get_brand_logo_url
from apps.orders.models import Order


logger = logging.getLogger(__name__)


def _build_tracking_email_context(*, order: Order, tracking_url: str, success_url: str) -> dict:
    split_url = urlsplit(tracking_url)
    base_url = f"{split_url.scheme}://{split_url.netloc}" if split_url.scheme and split_url.netloc else ""
    return {
        "order": order,
        "tracking_url": tracking_url,
        "success_url": success_url,
        "customer_name": order.customer_first_name or "there",
        "brand_name": "Nest & Whisk",
        "brand_logo_url": get_brand_logo_url(base_url=base_url),
        "brand_home_url": base_url or "/",
    }


def build_tracking_link_payload(*, order: Order, request) -> dict:
    return {
        "order_id": order.pk,
        "tracking_url": request.build_absolute_uri(
            reverse("checkout:tracking", kwargs={"order_number": order.order_number})
        ),
        "success_url": request.build_absolute_uri(
            reverse("checkout:success", kwargs={"order_number": order.order_number})
        ),
    }


def build_tracking_link_payloads(*, orders: list[Order], request) -> list[dict]:
    seen_order_ids: set[int] = set()
    payloads: list[dict] = []
    for order in orders:
        if order.pk in seen_order_ids:
            continue
        seen_order_ids.add(order.pk)
        payloads.append(build_tracking_link_payload(order=order, request=request))
    return payloads


def send_tracking_links_email_for_order(*, order_id: int, tracking_url: str, success_url: str) -> None:
    order = Order.objects.get(pk=order_id)
    context = _build_tracking_email_context(
        order=order,
        tracking_url=tracking_url,
        success_url=success_url,
    )
    subject = f"Your Nest & Whisk tracking links for {order.order_number}"
    text_body = render_to_string("emails/tracking_links.txt", context)
    html_body = render_to_string("emails/tracking_links.html", context)
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[order.customer_email],
    )
    email.attach_alternative(html_body, "text/html")
    email.send(fail_silently=False)


def send_tracking_links_email(*, order: Order, request) -> None:
    payload = build_tracking_link_payload(order=order, request=request)
    send_tracking_links_email_for_order(**payload)


def _build_order_confirmation_context(
    *, order: Order, tracking_url: str = "", success_url: str = ""
) -> dict:
    reference_url = tracking_url or success_url
    split_url = urlsplit(reference_url) if reference_url else None
    base_url = (
        f"{split_url.scheme}://{split_url.netloc}"
        if split_url and split_url.scheme and split_url.netloc
        else ""
    )
    return {
        "order": order,
        "tracking_url": tracking_url,
        "success_url": success_url,
        "customer_name": order.customer_first_name or "there",
        "brand_name": "Nest & Whisk",
        "brand_logo_url": get_brand_logo_url(base_url=base_url),
        "brand_home_url": base_url or "/",
    }


def send_order_confirmation_email_for_order(
    *, order_id: int, tracking_url: str = "", success_url: str = ""
) -> None:
    """Send a rich HTML + plain-text order confirmation to the customer."""
    order = Order.objects.prefetch_related("items").get(pk=order_id)
    if not order.customer_email:
        logger.warning("Order %s has no customer_email; skipping confirmation.", order.order_number)
        return
    context = _build_order_confirmation_context(
        order=order, tracking_url=tracking_url, success_url=success_url
    )
    subject = f"Nest & Whisk — order {order.order_number} confirmed"
    text_body = render_to_string("emails/order_confirmation.txt", context)
    html_body = render_to_string("emails/order_confirmation.html", context)
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[order.customer_email],
        reply_to=[getattr(settings, "CONTACT_EMAIL", settings.DEFAULT_FROM_EMAIL)],
    )
    email.attach_alternative(html_body, "text/html")
    email.send(fail_silently=False)


def send_order_confirmation_email(*, order: Order, request=None) -> bool:
    """Fire an order-confirmation email. Never raises — returns True on success.

    Safe to call from a view: SMTP / template failures are logged and swallowed
    so they never break the checkout flow.
    """
    tracking_url = ""
    success_url = ""
    if request is not None:
        try:
            tracking_url = request.build_absolute_uri(
                reverse("checkout:tracking", kwargs={"order_number": order.order_number})
            )
            success_url = request.build_absolute_uri(
                reverse("checkout:success", kwargs={"order_number": order.order_number})
            )
        except Exception:  # pragma: no cover - URL resolution should not fail
            logger.exception("Could not build absolute URLs for order %s", order.order_number)
    try:
        send_order_confirmation_email_for_order(
            order_id=order.pk,
            tracking_url=tracking_url,
            success_url=success_url,
        )
        return True
    except Exception:
        logger.exception(
            "Failed to send order confirmation email for order %s to %s",
            order.order_number,
            order.customer_email,
        )
        return False

