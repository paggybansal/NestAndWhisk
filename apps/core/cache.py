"""
Small read-through cache helper for view-layer querysets.

Why the view-layer and not template ``{% cache %}``?
    * The page includes per-user state (``cart_snapshot`` context processor,
      auth-dependent header) that must stay dynamic. Template caching around
      that data is brittle.
    * Catalog / homepage querysets are identical for every anonymous visitor
      and almost identical for logged-in users too. Caching the **result**
      of the DB call gives ~100% of the speedup with none of the per-user
      complication.

Values are pickled into the default cache (Redis in prod; LocMem fallback
locally), so pass materialised objects (``list(...)``) rather than lazy
``QuerySet``s — a pickled QuerySet still lazy-evaluates on unpickle.

Invalidation is TTL-based. Short defaults (60–300 s) keep admin edits
visible quickly without needing signal wiring on every related model.
"""

from __future__ import annotations

from typing import Callable, TypeVar

from django.core.cache import cache

T = TypeVar("T")


def cached(key: str, ttl: int, loader: Callable[[], T]) -> T:
    """Return ``loader()`` result, caching it under ``key`` for ``ttl`` seconds."""
    value = cache.get(key)
    if value is None:
        value = loader()
        cache.set(key, value, ttl)
    return value


def bust(*keys: str) -> None:
    """Drop one or more cache keys. Useful from signal handlers / admin save."""
    cache.delete_many(list(keys))

