from __future__ import annotations

from dataclasses import dataclass, asdict
import re

_SPACE_RE = re.compile(r"\s+")

_DELHI_NCR_CITY_ALIASES = {
    "delhi": "Delhi",
    "new delhi": "New Delhi",
    "gurgaon": "Gurugram",
    "gurugram": "Gurugram",
    "noida": "Noida",
    "greater noida": "Greater Noida",
    "ghaziabad": "Ghaziabad",
    "faridabad": "Faridabad",
}

_DELHI_NCR_PINCODE_RANGES = (
    (110001, 110099),
    (121001, 121013),
    (122001, 122022),
    (201001, 201017),
    (201301, 201318),
)


@dataclass(slots=True)
class DelhiNcrDeliveryExperience:
    status: str
    badge: str
    pill: str
    coverage_summary: str
    sample_postal_codes: str
    headline: str
    body: str
    eta: str
    matched_city: str = ""
    normalized_postal_code: str = ""
    is_express_zone: bool = False

    def to_dict(self) -> dict[str, str | bool]:
        return asdict(self)


def _normalize_text(value: str) -> str:
    cleaned = _SPACE_RE.sub(" ", (value or "").strip().lower())
    return cleaned.replace(",", " ").replace("-", " ").strip()


def normalize_postal_code(value: str) -> str:
    return "".join(character for character in (value or "") if character.isdigit())[:6]


def _match_city(value: str) -> str:
    normalized_value = _normalize_text(value)
    return _DELHI_NCR_CITY_ALIASES.get(normalized_value, "")


def _is_delhi_ncr_postal_code(value: str) -> bool:
    if len(value) != 6:
        return False
    code = int(value)
    return any(start <= code <= end for start, end in _DELHI_NCR_PINCODE_RANGES)


def get_delhi_ncr_delivery_experience(*, city: str = "", postal_code: str = "") -> dict[str, str | bool]:
    matched_city = _match_city(city)
    normalized_postal_code = normalize_postal_code(postal_code)
    postal_match = _is_delhi_ncr_postal_code(normalized_postal_code)

    shared = {
        "badge": "Delhi NCR local delivery",
        "pill": "Same-day / next-day in select Delhi NCR areas",
        "coverage_summary": "Coverage commonly includes Delhi, Gurugram, Noida, Greater Noida, Ghaziabad, and Faridabad, while nationwide shipping remains available beyond NCR.",
        "sample_postal_codes": "110001, 122002, 201301, 121001",
        "matched_city": matched_city,
        "normalized_postal_code": normalized_postal_code,
    }

    if matched_city and postal_match:
        return DelhiNcrDeliveryExperience(
            status="eligible",
            headline="Great news — this address looks eligible for Delhi NCR local delivery.",
            body=f"{matched_city} with postal code {normalized_postal_code} sits within our current Delhi NCR guidance zone for faster local delivery planning.",
            eta="Earlier orders may qualify for same-day dispatch, while most covered Delhi NCR deliveries are planned for next-day arrival.",
            is_express_zone=True,
            **shared,
        ).to_dict()

    if matched_city and not normalized_postal_code:
        return DelhiNcrDeliveryExperience(
            status="city_match",
            headline=f"{matched_city} is part of our Delhi NCR delivery zone.",
            body="Add the postal code and we’ll show the best guidance we can for local delivery timing at checkout.",
            eta="Same-day dispatch may be possible on earlier orders, with next-day delivery across select NCR neighbourhoods.",
            is_express_zone=True,
            **shared,
        ).to_dict()

    if postal_match and not matched_city:
        return DelhiNcrDeliveryExperience(
            status="postal_match",
            headline=f"Postal code {normalized_postal_code} looks like a Delhi NCR delivery match.",
            body="Add the city as well so we can confirm the clearest local-delivery guidance for this address.",
            eta="This postal code falls inside our Delhi NCR guidance range for faster local planning.",
            is_express_zone=True,
            **shared,
        ).to_dict()

    if matched_city and normalized_postal_code and not postal_match:
        return DelhiNcrDeliveryExperience(
            status="city_conflict",
            headline=f"We recognize {matched_city}, but postal code {normalized_postal_code} sits outside our usual Delhi NCR express range.",
            body="We can still ship nationwide, though the faster Delhi NCR delivery timing may not apply for this address.",
            eta="If this is an event, gift window, or urgent order, our team can still help you plan the best dispatch timing.",
            **shared,
        ).to_dict()

    if normalized_postal_code:
        return DelhiNcrDeliveryExperience(
            status="outside",
            headline="This address does not currently look like a Delhi NCR local-delivery match.",
            body="Nest & Whisk still delivers nationwide, but Delhi NCR same-day or next-day timing may not apply here.",
            eta="Use delivery notes for timing requests and our team can help guide gifting or event orders.",
            **shared,
        ).to_dict()

    return DelhiNcrDeliveryExperience(
        status="default",
        headline="Delhi NCR orders may qualify for faster local delivery.",
        body="Enter a Delhi, Gurugram, Noida, Greater Noida, Ghaziabad, or Faridabad address to see our best local delivery guidance at checkout.",
        eta="We support same-day or next-day planning in select Delhi NCR pincodes, while keeping nationwide shipping available elsewhere.",
        **shared,
    ).to_dict()
