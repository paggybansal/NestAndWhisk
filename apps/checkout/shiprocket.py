from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib import error, parse, request

from django.conf import settings
from django.core.cache import cache

from apps.core.delivery import get_delhi_ncr_delivery_experience, normalize_postal_code

_SHIPROCKET_TOKEN_CACHE_KEY = "checkout:shiprocket:auth_token"
_SHIPROCKET_TOKEN_TTL_SECONDS = 9 * 24 * 60 * 60


class ShiprocketConfigurationError(Exception):
    pass


class ShiprocketLookupError(Exception):
    pass


def shiprocket_is_configured() -> bool:
    return bool(
        settings.SHIPROCKET_ENABLED
        and settings.SHIPROCKET_EMAIL
        and settings.SHIPROCKET_PASSWORD
        and settings.SHIPROCKET_PICKUP_POSTCODE
    )


def _shiprocket_base_url() -> str:
    return settings.SHIPROCKET_BASE_URL.rstrip("/")


def _shiprocket_headers(*, token: str = "") -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _shiprocket_api_request(*, method: str, path: str, payload: dict[str, Any] | None = None, token: str = "") -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = request.Request(
        url=f"{_shiprocket_base_url()}{path}",
        data=body,
        headers=_shiprocket_headers(token=token),
        method=method.upper(),
    )
    try:
        with request.urlopen(req, timeout=settings.SHIPROCKET_TIMEOUT_SECONDS) as response:
            raw = response.read().decode("utf-8")
    except error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")
        raise ShiprocketLookupError(f"Shiprocket request failed with HTTP {exc.code}: {details or exc.reason}") from exc
    except error.URLError as exc:
        raise ShiprocketLookupError("Shiprocket delivery lookup could not reach the API.") from exc

    if not raw.strip():
        return {}

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ShiprocketLookupError("Shiprocket returned an invalid JSON response.") from exc


def _get_shiprocket_auth_token(*, force_refresh: bool = False) -> str:
    if not shiprocket_is_configured():
        raise ShiprocketConfigurationError("Shiprocket delivery lookup is not configured.")

    if not force_refresh:
        cached_token = cache.get(_SHIPROCKET_TOKEN_CACHE_KEY)
        if cached_token:
            return str(cached_token)

    response = _shiprocket_api_request(
        method="POST",
        path="/auth/login",
        payload={
            "email": settings.SHIPROCKET_EMAIL,
            "password": settings.SHIPROCKET_PASSWORD,
        },
    )
    token = response.get("token") or response.get("data", {}).get("token", "")
    if not token:
        raise ShiprocketLookupError("Shiprocket authentication succeeded without returning a token.")

    cache.set(_SHIPROCKET_TOKEN_CACHE_KEY, token, timeout=_SHIPROCKET_TOKEN_TTL_SECONDS)
    return str(token)


def _parse_eta_days(company: dict[str, Any]) -> int | None:
    for key in ("estimated_delivery_days", "delivery_days", "etd"):
        value = company.get(key)
        if value in (None, "", False):
            continue
        try:
            numeric = Decimal(str(value))
        except (InvalidOperation, ValueError):
            continue
        return max(0, int(numeric))
    return None


def _get_available_couriers(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data", {}) if isinstance(payload, dict) else {}
    couriers = data.get("available_courier_companies") or payload.get("available_courier_companies") or []
    return [company for company in couriers if isinstance(company, dict)]


def _select_best_courier(couriers: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not couriers:
        return None
    return min(
        couriers,
        key=lambda company: (
            _parse_eta_days(company) is None,
            _parse_eta_days(company) or 999,
            str(company.get("courier_name", "zzz")),
        ),
    )


def lookup_shiprocket_delivery_estimate(*, postal_code: str) -> dict[str, Any]:
    normalized_postal_code = normalize_postal_code(postal_code)
    if len(normalized_postal_code) != 6:
        raise ShiprocketLookupError("A valid 6-digit postal code is required for Shiprocket delivery lookup.")

    token = _get_shiprocket_auth_token()
    query = parse.urlencode(
        {
            "pickup_postcode": settings.SHIPROCKET_PICKUP_POSTCODE,
            "delivery_postcode": normalized_postal_code,
            "weight": settings.SHIPROCKET_DEFAULT_PACKAGE_WEIGHT_KG,
            "cod": 0,
        }
    )

    try:
        payload = _shiprocket_api_request(
            method="GET",
            path=f"/courier/serviceability/?{query}",
            token=token,
        )
    except ShiprocketLookupError as exc:
        if "HTTP 401" not in str(exc):
            raise
        token = _get_shiprocket_auth_token(force_refresh=True)
        payload = _shiprocket_api_request(
            method="GET",
            path=f"/courier/serviceability/?{query}",
            token=token,
        )

    couriers = _get_available_couriers(payload)
    best_courier = _select_best_courier(couriers)
    return {
        "payload": payload,
        "courier_count": len(couriers),
        "best_courier": best_courier,
        "estimated_days": _parse_eta_days(best_courier or {}),
    }


def get_checkout_delivery_experience(*, city: str = "", postal_code: str = "") -> dict[str, Any]:
    fallback = get_delhi_ncr_delivery_experience(city=city, postal_code=postal_code)
    fallback.update(
        {
            "source": "fallback",
            "provider": "local",
            "live_eta_available": False,
            "shiprocket_available": shiprocket_is_configured(),
            "shiprocket_error": "",
            "serviceable": bool(fallback.get("is_express_zone")),
            "courier_name": "",
            "courier_count": 0,
            "eta_days": None,
            "status_note": "Guided by storefront delivery rules.",
        }
    )

    normalized_postal_code = normalize_postal_code(postal_code)
    if len(normalized_postal_code) != 6:
        return fallback

    if not shiprocket_is_configured():
        fallback["shiprocket_error"] = "Shiprocket is not configured in this environment."
        return fallback

    try:
        lookup = lookup_shiprocket_delivery_estimate(postal_code=normalized_postal_code)
    except (ShiprocketConfigurationError, ShiprocketLookupError) as exc:
        fallback["shiprocket_error"] = str(exc)
        return fallback

    best_courier = lookup.get("best_courier")
    courier_count = int(lookup.get("courier_count") or 0)
    eta_days = lookup.get("estimated_days")
    if not best_courier:
        fallback.update(
            {
                "source": "shiprocket",
                "provider": "shiprocket",
                "shiprocket_available": True,
                "status": "live_unavailable",
                "headline": "Live courier availability could not confirm serviceability for this postal code.",
                "body": "We could not find an active courier option from Shiprocket for this pincode just now, so we’re showing our guided delivery message instead.",
                "eta": "Courier availability can change through the day. Please review again later or contact the team for help with urgent gifting.",
                "coverage_summary": "Fallback guidance is still available below while live courier availability is unavailable.",
                "serviceable": False,
                "courier_count": courier_count,
                "status_note": "Live courier lookup returned no serviceable options.",
            }
        )
        return fallback

    courier_name = str(best_courier.get("courier_name") or best_courier.get("name") or "Shiprocket courier")
    eta_copy = (
        "Estimated next-day delivery based on the current courier response."
        if eta_days == 1
        else f"Estimated delivery in about {eta_days} day(s) based on the current courier response."
        if eta_days is not None
        else "A live courier option is available now, though Shiprocket did not return a numeric ETA."
    )

    fallback.update(
        {
            "source": "shiprocket",
            "provider": "shiprocket",
            "shiprocket_available": True,
            "live_eta_available": eta_days is not None,
            "status": "live_eligible",
            "badge": "Live Shiprocket ETA",
            "pill": "Real-time courier estimate",
            "headline": f"Live Shiprocket estimate available for {normalized_postal_code}.",
            "body": f"{courier_name} currently looks like the fastest available courier for this destination based on Shiprocket’s serviceability lookup.",
            "eta": eta_copy,
            "coverage_summary": "Live ETA depends on dispatch cut-off time, packaging readiness, courier allocation, and serviceability at lookup time.",
            "serviceable": True,
            "courier_name": courier_name,
            "courier_count": courier_count,
            "eta_days": eta_days,
            "status_note": "Powered by Shiprocket live courier serviceability.",
        }
    )
    return fallback
