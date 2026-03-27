from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from urllib.parse import urlsplit

from apps.core.branding import get_brand_logo_url
from apps.orders.models import Order


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
