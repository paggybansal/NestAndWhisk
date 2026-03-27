import pytest
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse

from apps.checkout.shiprocket import get_checkout_delivery_experience, lookup_shiprocket_delivery_estimate


@pytest.mark.django_db
@override_settings(
    SHIPROCKET_ENABLED=False,
    SHIPROCKET_EMAIL="",
    SHIPROCKET_PASSWORD="",
    SHIPROCKET_PICKUP_POSTCODE="",
)
def test_checkout_delivery_experience_uses_fallback_when_shiprocket_is_not_configured():
    experience = get_checkout_delivery_experience(city="Delhi", postal_code="110001")

    assert experience["source"] == "fallback"
    assert experience["provider"] == "local"
    assert experience["shiprocket_available"] is False
    assert experience["status"] == "eligible"


@pytest.mark.django_db
@override_settings(
    SHIPROCKET_ENABLED=True,
    SHIPROCKET_EMAIL="ops@example.com",
    SHIPROCKET_PASSWORD="super-secret",
    SHIPROCKET_PICKUP_POSTCODE="110020",
)
def test_lookup_shiprocket_delivery_estimate_parses_fastest_courier(monkeypatch):
    cache.clear()

    responses = iter(
        [
            {"token": "shiprocket-token"},
            {
                "data": {
                    "available_courier_companies": [
                        {"courier_name": "Delhivery", "estimated_delivery_days": 2},
                        {"courier_name": "Blue Dart", "estimated_delivery_days": 1},
                    ]
                }
            },
        ]
    )

    def fake_api_request(**_kwargs):
        return next(responses)

    monkeypatch.setattr("apps.checkout.shiprocket._shiprocket_api_request", fake_api_request)

    lookup = lookup_shiprocket_delivery_estimate(postal_code="110001")

    assert lookup["courier_count"] == 2
    assert lookup["best_courier"]["courier_name"] == "Blue Dart"
    assert lookup["estimated_days"] == 1


@pytest.mark.django_db
@override_settings(
    SHIPROCKET_ENABLED=True,
    SHIPROCKET_EMAIL="ops@example.com",
    SHIPROCKET_PASSWORD="super-secret",
    SHIPROCKET_PICKUP_POSTCODE="110020",
)
def test_checkout_delivery_experience_prefers_shiprocket_live_eta_when_available(monkeypatch):
    cache.clear()

    responses = iter(
        [
            {"token": "shiprocket-token"},
            {
                "data": {
                    "available_courier_companies": [
                        {"courier_name": "Blue Dart", "estimated_delivery_days": 1},
                    ]
                }
            },
        ]
    )

    def fake_api_request(**_kwargs):
        return next(responses)

    monkeypatch.setattr("apps.checkout.shiprocket._shiprocket_api_request", fake_api_request)

    experience = get_checkout_delivery_experience(city="Delhi", postal_code="110001")

    assert experience["source"] == "shiprocket"
    assert experience["provider"] == "shiprocket"
    assert experience["live_eta_available"] is True
    assert experience["courier_name"] == "Blue Dart"
    assert experience["eta_days"] == 1
    assert experience["headline"] == "Live Shiprocket estimate available for 110001."


@pytest.mark.django_db
def test_delivery_lookup_endpoint_returns_json_payload(client, monkeypatch):
    monkeypatch.setattr(
        "apps.checkout.views.get_checkout_delivery_experience",
        lambda **_kwargs: {
            "status": "live_eligible",
            "badge": "Live Shiprocket ETA",
            "headline": "Live Shiprocket estimate available for 110001.",
            "body": "Blue Dart currently looks like the fastest available courier.",
            "eta": "Estimated next-day delivery based on the current courier response.",
            "coverage_summary": "Live ETA depends on courier allocation.",
            "source": "shiprocket",
            "provider": "shiprocket",
            "live_eta_available": True,
            "shiprocket_available": True,
            "shiprocket_error": "",
            "serviceable": True,
            "courier_name": "Blue Dart",
            "courier_count": 2,
            "eta_days": 1,
            "status_note": "Powered by Shiprocket live courier serviceability.",
            "is_express_zone": True,
        },
    )

    response = client.get(reverse("checkout:delivery_lookup"), {"city": "Delhi", "postal_code": "110001"})
    payload = response.json()

    assert response.status_code == 200
    assert payload["ok"] is True
    assert payload["provider"] == "shiprocket"
    assert payload["courier_name"] == "Blue Dart"
