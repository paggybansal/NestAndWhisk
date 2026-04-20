"""PhonePe PG Checkout V2 integration (OAuth `client_credentials`).

V2 replaces the legacy Hermes `/pg/v1/*` SHA256 X-VERIFY handshake with an
OAuth2 access token. Lifecycle:

  1. POST  /v1/oauth/token          → `access_token` (valid ~1 hour)
  2. POST  /checkout/v2/pay         → creates order, returns hosted `redirectUrl`
  3. GET   /checkout/v2/order/{merchantOrderId}/status?details=true
  4. POST  /payments/v2/refund
  5. S2S callback → Authorization header = sha256(username + ":" + password)

All amounts are in **paise**.  Modeled on the Stripe integration so the existing
Order / Payment / PaymentEvent / PaymentWebhookEvent lifecycle stays uniform.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import threading
import time
import uuid
from decimal import Decimal
from typing import Any

import requests
from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from apps.orders.models import Order, Payment, PaymentEvent, PaymentWebhookEvent
from apps.orders.services import (
    mark_payment_cancelled,
    mark_payment_failed,
    mark_payment_processing,
    mark_payment_refunded,
    mark_payment_succeeded,
)

logger = logging.getLogger(__name__)

PROVIDER_KEY = "phonepe"

# ---- V2 API paths ----
PATH_OAUTH_TOKEN = "/v1/oauth/token"
PATH_CREATE_ORDER = "/checkout/v2/pay"
PATH_ORDER_STATUS_TEMPLATE = "/checkout/v2/order/{merchant_order_id}/status"
PATH_REFUND = "/payments/v2/refund"
PATH_REFUND_STATUS_TEMPLATE = "/payments/v2/refund/{merchant_refund_id}/status"

# Terminal PhonePe order states we translate to our Payment.Status choices.
STATE_COMPLETED = "COMPLETED"
STATE_PENDING = "PENDING"
STATE_FAILED = "FAILED"
STATE_CANCELLED = "CANCELLED"


class PhonePeConfigurationError(Exception):
    """PhonePe credentials / URLs missing or malformed."""


class PhonePeAPIError(Exception):
    """Non-2xx response, malformed JSON, or network error."""


class PhonePeAuthError(Exception):
    """Received a 401 from PhonePe — token invalid; caller may retry once."""


class PhonePeChecksumError(Exception):
    """Callback Authorization header does not match."""


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def _require_config() -> tuple[str, str, str, str, int]:
    """Return (base_url, client_id, client_secret, client_version, timeout)."""
    client_id = settings.PHONEPE_CLIENT_ID
    client_secret = settings.PHONEPE_CLIENT_SECRET
    client_version = str(settings.PHONEPE_CLIENT_VERSION or "1")
    env_name = (settings.PHONEPE_ENV or "SANDBOX").upper()
    timeout = int(settings.PHONEPE_TIMEOUT_SECONDS or 15)

    if not client_id or not client_secret:
        raise PhonePeConfigurationError(
            "PHONEPE_CLIENT_ID and PHONEPE_CLIENT_SECRET must be set in environment."
        )

    base_url = (
        settings.PHONEPE_BASE_URL_PRODUCTION
        if env_name == "PRODUCTION"
        else settings.PHONEPE_BASE_URL_SANDBOX
    )
    if not base_url:
        raise PhonePeConfigurationError(f"PhonePe base URL not configured for env={env_name}")

    return base_url.rstrip("/"), client_id, client_secret, client_version, timeout


# ---------------------------------------------------------------------------
# OAuth token cache  (process-local, thread-safe, auto-refresh)
# ---------------------------------------------------------------------------

_TOKEN_CACHE: dict[str, Any] = {"access_token": None, "expires_at": 0.0}
_TOKEN_LOCK = threading.Lock()
_TOKEN_EARLY_REFRESH_SECONDS = 60


def _fetch_oauth_token(*, force: bool = False) -> str:
    """Return a valid access_token, fetching+caching on demand."""
    with _TOKEN_LOCK:
        now = time.time()
        cached_token = _TOKEN_CACHE.get("access_token")
        cached_exp = float(_TOKEN_CACHE.get("expires_at") or 0)
        if (
            not force
            and cached_token
            and cached_exp - _TOKEN_EARLY_REFRESH_SECONDS > now
        ):
            return cached_token

        base_url, client_id, client_secret, client_version, timeout = _require_config()
        env_name = (settings.PHONEPE_ENV or "SANDBOX").upper()
        auth_base = (
            settings.PHONEPE_AUTH_BASE_URL_PRODUCTION
            if env_name == "PRODUCTION"
            else settings.PHONEPE_AUTH_BASE_URL_SANDBOX
        ) or base_url
        url = f"{auth_base.rstrip('/')}{PATH_OAUTH_TOKEN}"
        form = {
            "client_id": client_id,
            "client_secret": client_secret,
            "client_version": client_version,
            "grant_type": "client_credentials",
        }
        try:
            resp = requests.post(
                url,
                data=form,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=timeout,
            )
        except requests.RequestException as exc:
            raise PhonePeAPIError(f"OAuth token network error: {exc}") from exc

        try:
            data = resp.json()
        except ValueError as exc:
            raise PhonePeAPIError(
                f"OAuth token non-JSON response (HTTP {resp.status_code}): {resp.text[:200]}"
            ) from exc

        if resp.status_code != 200 or "access_token" not in data:
            logger.error("PhonePe OAuth rejected: %s %s", resp.status_code, data)
            raise PhonePeAuthError(
                data.get("message")
                or data.get("error_description")
                or f"PhonePe OAuth failed (HTTP {resp.status_code})"
            )

        token = data["access_token"]
        expires_at = float(
            data.get("expires_at")
            or (time.time() + int(data.get("expires_in") or 3600))
        )
        _TOKEN_CACHE["access_token"] = token
        _TOKEN_CACHE["expires_at"] = expires_at
        logger.info(
            "PhonePe OAuth token refreshed env=%s expires_in=%ss",
            settings.PHONEPE_ENV,
            int(expires_at - time.time()),
        )
        return token


def _auth_headers(*, token: str | None = None) -> dict[str, str]:
    tok = token or _fetch_oauth_token()
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"O-Bearer {tok}",
    }


def _request_with_retry(
    method: str,
    url: str,
    *,
    json_body: dict | None = None,
    timeout: int,
) -> requests.Response:
    """Authenticated request; retries once after token refresh on 401."""
    try:
        resp = requests.request(
            method, url, headers=_auth_headers(), json=json_body, timeout=timeout
        )
    except requests.RequestException as exc:
        raise PhonePeAPIError(f"Network error: {exc}") from exc
    if resp.status_code == 401:
        logger.warning("PhonePe 401 — refreshing token and retrying once")
        _fetch_oauth_token(force=True)
        try:
            resp = requests.request(
                method, url, headers=_auth_headers(), json=json_body, timeout=timeout
            )
        except requests.RequestException as exc:
            raise PhonePeAPIError(f"Network error on retry: {exc}") from exc
    return resp


# ---------------------------------------------------------------------------
# Merchant order id
# ---------------------------------------------------------------------------

def generate_merchant_order_id(*, payment: Payment) -> str:
    """Unique per attempt, stable within the same attempt. Max 63 chars in V2."""
    return f"{payment.order.order_number}P{payment.pk}T{uuid.uuid4().hex[:8].upper()}"[:63]


# ---------------------------------------------------------------------------
# Create order — hosted PG_CHECKOUT
# ---------------------------------------------------------------------------

def initiate_payment(*, order: Order, payment: Payment, request) -> str:
    """POST /checkout/v2/pay. Returns hosted checkout URL."""
    base_url, _, _, _, timeout = _require_config()

    merchant_order_id = payment.provider_checkout_id or generate_merchant_order_id(payment=payment)

    redirect_url = request.build_absolute_uri(
        reverse("checkout:phonepe_redirect", kwargs={"order_number": order.order_number})
    )

    amount_paise = int((order.total * Decimal("100")).quantize(Decimal("1")))
    if amount_paise < 100:
        raise PhonePeAPIError(
            f"PhonePe minimum transaction amount is 100 paise (₹1); got {amount_paise}."
        )

    body: dict[str, Any] = {
        "merchantOrderId": merchant_order_id,
        "amount": amount_paise,
        "expireAfter": 1200,  # seconds; 20 minutes
        "metaInfo": {
            "udf1": f"order={order.order_number}",
            "udf2": f"payment={payment.pk}",
        },
        "paymentFlow": {
            "type": "PG_CHECKOUT",
            "message": f"Nest & Whisk order {order.order_number}",
            "merchantUrls": {"redirectUrl": redirect_url},
        },
    }

    logger.info(
        "PhonePe V2 pay-init order=%s merchantOrderId=%s amount_paise=%s env=%s",
        order.order_number, merchant_order_id, amount_paise, settings.PHONEPE_ENV,
    )

    resp = _request_with_retry(
        "POST", f"{base_url}{PATH_CREATE_ORDER}", json_body=body, timeout=timeout
    )
    try:
        data = resp.json()
    except ValueError as exc:
        raise PhonePeAPIError(
            f"Non-JSON from PhonePe (HTTP {resp.status_code}): {resp.text[:200]}"
        ) from exc

    if resp.status_code != 200:
        logger.error("PhonePe pay-init rejected order=%s body=%s", order.order_number, data)
        raise PhonePeAPIError(
            data.get("message") or data.get("error") or f"PhonePe rejected request (HTTP {resp.status_code})"
        )

    checkout_url = data.get("redirectUrl") or data.get("url", "")
    if not checkout_url:
        raise PhonePeAPIError("PhonePe V2 response missing redirectUrl")

    existing_prefs = (
        payment.raw_response.get("checkout_preferences", {})
        if isinstance(payment.raw_response, dict)
        else {}
    )
    mark_payment_processing(
        payment=payment,
        checkout_id=merchant_order_id,
        payment_id=data.get("orderId", ""),
        provider_reference=data.get("state", ""),
        raw_response={
            **(payment.raw_response if isinstance(payment.raw_response, dict) else {}),
            "checkout_preferences": {
                **existing_prefs,
                "payment_provider": PROVIDER_KEY,
                "currency": order.currency,
            },
            "phonepe_v2_create_order": data,
        },
    )
    _record_payment_event(payment=payment, event_type="phonepe.v2.order.created", data=data)

    if order.provider != PROVIDER_KEY:
        order.provider = PROVIDER_KEY
        order.save(update_fields=["provider", "updated_at"])

    return checkout_url


# ---------------------------------------------------------------------------
# Status check
# ---------------------------------------------------------------------------

def fetch_payment_status(*, merchant_order_id: str, details: bool = True) -> dict:
    """GET /checkout/v2/order/{merchantOrderId}/status"""
    base_url, _, _, _, timeout = _require_config()
    path = PATH_ORDER_STATUS_TEMPLATE.format(merchant_order_id=merchant_order_id)
    url = f"{base_url}{path}"
    if details:
        url += "?details=true"

    resp = _request_with_retry("GET", url, timeout=timeout)
    try:
        data = resp.json()
    except ValueError as exc:
        raise PhonePeAPIError(
            f"Status returned non-JSON (HTTP {resp.status_code})"
        ) from exc

    if resp.status_code >= 500:
        raise PhonePeAPIError(f"PhonePe status 5xx (HTTP {resp.status_code}): {data}")
    return data


def reconcile_payment(*, merchant_order_id: str) -> Payment | None:
    """Poll PhonePe status, persist. Safe to call repeatedly."""
    payment = (
        Payment.objects.filter(provider=PROVIDER_KEY, provider_checkout_id=merchant_order_id)
        .select_related("order")
        .first()
    )
    if payment is None:
        logger.warning("PhonePe reconcile: no payment for merchantOrderId=%s", merchant_order_id)
        return None
    if payment.status in {Payment.Status.SUCCEEDED, Payment.Status.REFUNDED}:
        return payment

    try:
        data = fetch_payment_status(merchant_order_id=merchant_order_id)
    except PhonePeAPIError:
        logger.exception("PhonePe reconcile failed for %s", merchant_order_id)
        return payment
    _apply_state_response(payment=payment, data=data)
    return payment


# ---------------------------------------------------------------------------
# Callback (S2S webhook)
# ---------------------------------------------------------------------------

def _expected_callback_authorization() -> str:
    """sha256(username + ":" + password) as hex — V2 callback signature scheme."""
    user = settings.PHONEPE_CALLBACK_USERNAME or ""
    password = settings.PHONEPE_CALLBACK_PASSWORD or ""
    return hashlib.sha256(f"{user}:{password}".encode("utf-8")).hexdigest()


def verify_callback_authorization(received_header: str) -> bool:
    """Constant-time compare. Requires PHONEPE_CALLBACK_USERNAME / _PASSWORD."""
    if not received_header:
        return False
    expected = _expected_callback_authorization()
    return hmac.compare_digest(expected, received_header.strip())


def handle_callback(*, authorization_header: str, raw_body: bytes) -> PaymentWebhookEvent:
    """Idempotently process a PhonePe V2 webhook.

    Raises:
        PhonePeConfigurationError — if callback creds missing.
        PhonePeChecksumError       — if the Authorization header is invalid.
        PhonePeAPIError            — if body is not JSON.
    """
    if not settings.PHONEPE_CALLBACK_USERNAME or not settings.PHONEPE_CALLBACK_PASSWORD:
        raise PhonePeConfigurationError(
            "PHONEPE_CALLBACK_USERNAME and PHONEPE_CALLBACK_PASSWORD must be set "
            "(configure them in the PhonePe merchant dashboard → Webhooks → Username/Password)."
        )

    if not verify_callback_authorization(authorization_header):
        logger.warning("PhonePe V2 callback authorization mismatch")
        raise PhonePeChecksumError("Invalid Authorization header for PhonePe callback")

    try:
        body = json.loads(raw_body.decode("utf-8") or "{}")
    except ValueError as exc:
        raise PhonePeAPIError(f"Callback body is not JSON: {exc}") from exc

    event_type = body.get("event") or body.get("type") or "UNKNOWN"
    payload = body.get("payload") or body.get("data") or {}
    merchant_order_id = payload.get("merchantOrderId") or payload.get("merchantTransactionId") or ""
    phonepe_order_id = payload.get("orderId") or payload.get("transactionId") or ""

    event_id = f"phonepe:{merchant_order_id or phonepe_order_id}:{event_type}"
    webhook_event, created = PaymentWebhookEvent.objects.get_or_create(
        event_id=event_id,
        defaults={
            "provider": PROVIDER_KEY,
            "event_type": event_type,
            "object_id": merchant_order_id or phonepe_order_id,
            "payload": body,
        },
    )
    if webhook_event.is_processed and not created:
        logger.info("PhonePe V2 duplicate callback ignored event_id=%s", event_id)
        return webhook_event

    webhook_event.payload = body
    webhook_event.event_type = event_type
    webhook_event.object_id = merchant_order_id or phonepe_order_id
    webhook_event.save(update_fields=["payload", "event_type", "object_id", "updated_at"])

    payment = (
        Payment.objects.filter(provider=PROVIDER_KEY, provider_checkout_id=merchant_order_id)
        .select_related("order")
        .first()
    )
    note = _apply_state_response(payment=payment, data=payload) if payment else "order not found"

    webhook_event.payment = payment
    webhook_event.order = payment.order if payment else None
    webhook_event.is_processed = True
    webhook_event.processed_at = timezone.now()
    webhook_event.processing_notes = (note or event_type)[:255]
    webhook_event.save(
        update_fields=[
            "payment", "order", "is_processed", "processed_at", "processing_notes", "updated_at",
        ]
    )
    return webhook_event


# ---------------------------------------------------------------------------
# Refund
# ---------------------------------------------------------------------------

def initiate_refund(*, payment: Payment, amount: Decimal | None = None, reason: str = "") -> dict:
    """POST /payments/v2/refund. Only for succeeded PhonePe payments."""
    if payment.provider != PROVIDER_KEY:
        raise PhonePeAPIError(f"Payment {payment.pk} is not a PhonePe payment.")
    if payment.status != Payment.Status.SUCCEEDED:
        raise PhonePeAPIError(
            f"Cannot refund PhonePe payment in status={payment.status}; must be succeeded."
        )

    base_url, _, _, _, timeout = _require_config()
    refund_amount = amount if amount is not None else payment.amount
    refund_amount_paise = int((refund_amount * Decimal("100")).quantize(Decimal("1")))
    if refund_amount_paise <= 0 or refund_amount_paise > int(payment.amount * Decimal("100")):
        raise PhonePeAPIError("Refund amount out of range.")

    merchant_refund_id = f"R{payment.pk}-{uuid.uuid4().hex[:10].upper()}"[:63]

    body = {
        "merchantRefundId": merchant_refund_id,
        "originalMerchantOrderId": payment.provider_checkout_id,
        "amount": refund_amount_paise,
    }

    logger.info(
        "PhonePe V2 refund payment=%s merchantRefundId=%s amount_paise=%s",
        payment.pk, merchant_refund_id, refund_amount_paise,
    )

    resp = _request_with_retry(
        "POST", f"{base_url}{PATH_REFUND}", json_body=body, timeout=timeout
    )
    try:
        data = resp.json()
    except ValueError as exc:
        raise PhonePeAPIError(f"Refund non-JSON (HTTP {resp.status_code})") from exc

    _record_payment_event(
        payment=payment,
        event_type="phonepe.v2.refund.initiated",
        data={"request": {**body, "reason": reason}, "response": data},
        amount=refund_amount,
    )

    if resp.status_code != 200:
        logger.error("PhonePe V2 refund rejected payment=%s body=%s", payment.pk, data)
        raise PhonePeAPIError(
            data.get("message") or f"PhonePe refund rejected (HTTP {resp.status_code})"
        )

    mark_payment_refunded(
        payment=payment,
        provider_reference=merchant_refund_id,
        raw_response={
            **(payment.raw_response if isinstance(payment.raw_response, dict) else {}),
            "phonepe_v2_refund": data,
        },
    )
    return data


def fetch_refund_status(*, merchant_refund_id: str) -> dict:
    """GET /payments/v2/refund/{merchantRefundId}/status"""
    base_url, _, _, _, timeout = _require_config()
    path = PATH_REFUND_STATUS_TEMPLATE.format(merchant_refund_id=merchant_refund_id)
    resp = _request_with_retry("GET", f"{base_url}{path}", timeout=timeout)
    try:
        return resp.json()
    except ValueError as exc:
        raise PhonePeAPIError(f"Refund status non-JSON (HTTP {resp.status_code})") from exc


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

def _apply_state_response(*, payment: Payment, data: dict) -> str:
    """Translate a V2 order state into Payment status. Returns audit note."""
    if payment is None:
        return "order not found"

    state = (data.get("state") or data.get("status") or "").upper()
    phonepe_order_id = data.get("orderId") or data.get("transactionId") or ""
    payment_details = data.get("paymentDetails") or []
    instrument = (payment_details[0].get("paymentMode") if payment_details else "") or ""

    merged_raw = {
        **(payment.raw_response if isinstance(payment.raw_response, dict) else {}),
        "phonepe_v2_last_status": data,
        "phonepe_v2_last_instrument": instrument,
    }

    if state == STATE_COMPLETED:
        mark_payment_succeeded(
            payment=payment,
            provider_payment_id=phonepe_order_id,
            provider_reference=state,
            receipt_url="",
            raw_response=merged_raw,
        )
        _record_payment_event(payment=payment, event_type="phonepe.v2.succeeded", data=data)
        return "succeeded"

    if state == STATE_FAILED:
        mark_payment_failed(
            payment=payment, provider_reference=state, raw_response=merged_raw,
        )
        _record_payment_event(payment=payment, event_type="phonepe.v2.failed", data=data)
        return f"failed ({state})"

    if state == STATE_CANCELLED:
        mark_payment_cancelled(
            payment=payment, provider_reference=state, raw_response=merged_raw,
        )
        _record_payment_event(payment=payment, event_type="phonepe.v2.cancelled", data=data)
        return "cancelled"

    # PENDING / unknown — audit only, no terminal transition.
    payment.raw_response = merged_raw
    payment.provider_reference = state or payment.provider_reference
    if phonepe_order_id and not payment.provider_payment_id:
        payment.provider_payment_id = phonepe_order_id
    payment.save(update_fields=["raw_response", "provider_reference", "provider_payment_id", "updated_at"])
    _record_payment_event(payment=payment, event_type=f"phonepe.v2.{state.lower() or 'unknown'}", data=data)
    return f"pending ({state or 'unknown'})"


def _record_payment_event(*, payment: Payment, event_type: str, data: dict, amount: Decimal | None = None) -> None:
    PaymentEvent.objects.create(
        payment=payment,
        event_type=event_type,
        provider_reference=str(
            data.get("orderId") or data.get("transactionId") or data.get("state") or ""
        )[:255],
        amount=amount if amount is not None else payment.amount,
        currency=payment.currency,
        payload=data,
        occurred_at=timezone.now(),
    )

