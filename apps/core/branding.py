from __future__ import annotations

from pathlib import Path

from django.conf import settings

_BRAND_LOGO_CANDIDATES = ("Logo.png", "Logo.webp", "Logo.jpeg", "Logo.jpg")
_DEFAULT_BRAND_LOGO = "Logo.jpeg"


def get_brand_logo_path() -> str:
    media_root = Path(settings.MEDIA_ROOT)
    media_url = settings.MEDIA_URL.rstrip("/")

    for candidate in _BRAND_LOGO_CANDIDATES:
        if (media_root / candidate).exists():
            return f"{media_url}/{candidate}"

    return f"{media_url}/{_DEFAULT_BRAND_LOGO}"


def get_brand_logo_url(*, base_url: str = "") -> str:
    logo_path = get_brand_logo_path()
    return f"{base_url}{logo_path}" if base_url else logo_path
