"""Unit tests for PhonePe V2 gateway — OAuth, callback verify, idempotency."""
import hashlib
import json
import time
from unittest import mock

import pytest
from django.test import override_settings

from apps.checkout import phonepe as gateway


CLIENT_ID = "TESTCLIENT"
CLIENT_SECRET = "TESTSECRET"
CALLBACK_USER = "cb-user"
CALLBACK_PASS = "cb-pass"


def _settings():
    return override_settings(
        PHONEPE_ENV="SANDBOX",
        PHONEPE_CLIENT_ID=CLIENT_ID,
        PHONEPE_CLIENT_SECRET=CLIENT_SECRET,
        PHONEPE_CLIENT_VERSION="1",
        PHONEPE_CALLBACK_USERNAME=CALLBACK_USER,
        PHONEPE_CALLBACK_PASSWORD=CALLBACK_PASS,
        PHONEPE_BASE_URL_SANDBOX="https://sandbox.test",
        PHONEPE_BASE_URL_PRODUCTION="https://prod.test",
        PHONEPE_TIMEOUT_SECONDS=5,
    )


@pytest.fixture(autouse=True)
def _reset_token_cache():
    gateway._TOKEN_CACHE["access_token"] = None
    gateway._TOKEN_CACHE["expires_at"] = 0
    yield
    gateway._TOKEN_CACHE["access_token"] = None
    gateway._TOKEN_CACHE["expires_at"] = 0


class _Resp:
    def __init__(self, status, payload):
        self.status_code = status
        self._payload = payload
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


def test_require_config_raises_when_client_id_missing():
    with override_settings(
        PHONEPE_CLIENT_ID="", PHONEPE_CLIENT_SECRET="", PHONEPE_CLIENT_VERSION="1",
        PHONEPE_ENV="SANDBOX", PHONEPE_BASE_URL_SANDBOX="https://x",
        PHONEPE_BASE_URL_PRODUCTION="https://x",
    ):
        with pytest.raises(gateway.PhonePeConfigurationError):
            gateway._require_config()


def test_oauth_token_fetch_caches_until_near_expiry():
    with _settings():
        with mock.patch("apps.checkout.phonepe.requests.post") as post:
            post.return_value = _Resp(
                200,
                {"access_token": "T1", "token_type": "O-Bearer", "expires_at": time.time() + 3600},
            )
            t1 = gateway._fetch_oauth_token()
            t2 = gateway._fetch_oauth_token()
        assert t1 == t2 == "T1"
        assert post.call_count == 1


def test_oauth_token_rejects_on_bad_credentials():
    with _settings():
        with mock.patch("apps.checkout.phonepe.requests.post") as post:
            post.return_value = _Resp(401, {"error_description": "invalid_client"})
            with pytest.raises(gateway.PhonePeAuthError):
                gateway._fetch_oauth_token(force=True)


def test_verify_callback_authorization_accepts_correct_header():
    with _settings():
        header = hashlib.sha256(f"{CALLBACK_USER}:{CALLBACK_PASS}".encode()).hexdigest()
        assert gateway.verify_callback_authorization(header) is True


def test_verify_callback_authorization_rejects_tampered_header():
    with _settings():
        assert gateway.verify_callback_authorization("0" * 64) is False


def test_verify_callback_authorization_rejects_empty():
    with _settings():
        assert gateway.verify_callback_authorization("") is False


@pytest.mark.django_db
def test_handle_callback_rejects_bad_authorization():
    with _settings():
        body = json.dumps(
            {"event": "checkout.order.completed", "payload": {"merchantOrderId": "X"}}
        ).encode()
        with pytest.raises(gateway.PhonePeChecksumError):
            gateway.handle_callback(authorization_header="wrong", raw_body=body)


@pytest.mark.django_db
def test_handle_callback_records_event_for_unknown_order():
    from apps.orders.models import PaymentWebhookEvent
    with _settings():
        body_dict = {
            "event": "checkout.order.completed",
            "payload": {"merchantOrderId": "UNKNOWN-1", "orderId": "OMO123", "state": "COMPLETED"},
        }
        header = hashlib.sha256(f"{CALLBACK_USER}:{CALLBACK_PASS}".encode()).hexdigest()
        evt = gateway.handle_callback(
            authorization_header=header, raw_body=json.dumps(body_dict).encode()
        )
    assert evt.provider == "phonepe"
    assert evt.event_type == "checkout.order.completed"
    assert evt.is_processed is True
    assert evt.processing_notes == "order not found"
    assert PaymentWebhookEvent.objects.filter(object_id="UNKNOWN-1").count() == 1


@pytest.mark.django_db
def test_handle_callback_is_idempotent_on_duplicate_delivery():
    from apps.orders.models import PaymentWebhookEvent
    with _settings():
        body_dict = {
            "event": "checkout.order.completed",
            "payload": {"merchantOrderId": "DUP-1", "state": "COMPLETED"},
        }
        header = hashlib.sha256(f"{CALLBACK_USER}:{CALLBACK_PASS}".encode()).hexdigest()
        raw = json.dumps(body_dict).encode()
        gateway.handle_callback(authorization_header=header, raw_body=raw)
        gateway.handle_callback(authorization_header=header, raw_body=raw)
    assert PaymentWebhookEvent.objects.filter(object_id="DUP-1").count() == 1


@pytest.mark.django_db
def test_handle_callback_requires_callback_credentials():
    with override_settings(
        PHONEPE_ENV="SANDBOX", PHONEPE_CLIENT_ID=CLIENT_ID, PHONEPE_CLIENT_SECRET=CLIENT_SECRET,
        PHONEPE_CLIENT_VERSION="1", PHONEPE_CALLBACK_USERNAME="", PHONEPE_CALLBACK_PASSWORD="",
        PHONEPE_BASE_URL_SANDBOX="https://x", PHONEPE_BASE_URL_PRODUCTION="https://x",
        PHONEPE_TIMEOUT_SECONDS=5,
    ):
        with pytest.raises(gateway.PhonePeConfigurationError):
            gateway.handle_callback(authorization_header="anything", raw_body=b"{}")


def test_request_with_retry_refreshes_token_on_401():
    with _settings():
        gateway._TOKEN_CACHE["access_token"] = "OLD"
        gateway._TOKEN_CACHE["expires_at"] = time.time() + 3600
        with mock.patch("apps.checkout.phonepe.requests.request") as req, \
             mock.patch("apps.checkout.phonepe.requests.post") as post:
            req.side_effect = [_Resp(401, {"error": "expired"}), _Resp(200, {"ok": True})]
            post.return_value = _Resp(
                200,
                {"access_token": "NEW", "token_type": "O-Bearer", "expires_at": time.time() + 3600},
            )
            resp = gateway._request_with_retry("GET", "https://sandbox.test/x", timeout=5)
        assert resp.status_code == 200
        assert req.call_count == 2
        assert post.call_count == 1
