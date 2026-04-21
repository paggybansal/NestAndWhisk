"""Non-blocking email backend.

Wraps any underlying Django email backend and dispatches ``send_messages``
onto a bounded background thread pool. Request handlers return immediately;
slow / failing mail servers can no longer stall gunicorn workers or surface
500s to end users (e.g. signup → "verification email" on a flaky SMTP path).

Usage (settings / env):

    EMAIL_BACKEND = "apps.core.mail.AsyncEmailBackend"
    ASYNC_EMAIL_REAL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

Behaviour notes:
  * ``send_messages`` returns ``len(messages)`` synchronously (the contract
    callers expect) but the actual SMTP conversation happens off-thread.
  * Failures are logged to the ``apps.core.mail`` logger, never raised.
  * A module-level ``ThreadPoolExecutor`` is reused across requests; it is
    shut down gracefully via ``atexit`` so in-flight sends get a short
    grace period on process exit.
  * Tests can force synchronous behaviour with ``ASYNC_EMAIL_SYNC=True``
    (also auto-enabled when ``settings.TESTING`` is truthy, if set).
"""

from __future__ import annotations

import atexit
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Sequence

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.message import EmailMessage
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)

_DEFAULT_REAL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
_DEFAULT_MAX_WORKERS = 4
_SHUTDOWN_GRACE_SECONDS = 10

_executor: ThreadPoolExecutor | None = None
_executor_lock = threading.Lock()


def _get_executor() -> ThreadPoolExecutor:
    """Return (lazily create) the shared email thread pool."""
    global _executor
    if _executor is not None:
        return _executor
    with _executor_lock:
        if _executor is None:
            max_workers = getattr(
                settings, "ASYNC_EMAIL_MAX_WORKERS", _DEFAULT_MAX_WORKERS
            )
            _executor = ThreadPoolExecutor(
                max_workers=max_workers,
                thread_name_prefix="async-email",
            )
            atexit.register(_shutdown_executor)
    return _executor


def _shutdown_executor() -> None:
    """Flush outstanding sends on interpreter shutdown."""
    global _executor
    exe = _executor
    if exe is None:
        return
    _executor = None
    try:
        # Py3.9+: cancel_futures lets queued-but-not-started sends be dropped
        # rather than blocking shutdown forever if the pool is saturated.
        exe.shutdown(wait=True, cancel_futures=True)
    except Exception:  # pragma: no cover — defensive
        logger.exception("Async email executor shutdown failed")


def _send_in_thread(
    real_backend_path: str,
    messages: list[EmailMessage],
    fail_silently: bool,
) -> None:
    """Worker: open a fresh backend connection and send the batch."""
    try:
        backend_cls = import_string(real_backend_path)
        connection = backend_cls(fail_silently=fail_silently)
        sent = connection.send_messages(messages) or 0
        if sent != len(messages):
            logger.warning(
                "Async email: backend reported %d/%d messages sent",
                sent,
                len(messages),
            )
    except Exception:
        # Never re-raise — we're on a background thread; the originating
        # request already returned 200 to the user.
        subjects = ", ".join(
            (m.subject or "")[:60] for m in messages[:3]
        ) or "<no subject>"
        logger.exception(
            "Async email send failed (backend=%s, messages=%d, subjects=%s)",
            real_backend_path,
            len(messages),
            subjects,
        )


class AsyncEmailBackend(BaseEmailBackend):
    """Django email backend that returns immediately and sends off-thread."""

    def __init__(self, fail_silently: bool = False, **kwargs) -> None:
        super().__init__(fail_silently=fail_silently)
        self._real_backend_path: str = getattr(
            settings, "ASYNC_EMAIL_REAL_BACKEND", _DEFAULT_REAL_BACKEND
        )
        # Guard against recursion if someone misconfigures the wrapper to
        # point at itself.
        if self._real_backend_path.endswith("AsyncEmailBackend"):
            raise ValueError(
                "ASYNC_EMAIL_REAL_BACKEND must not be AsyncEmailBackend "
                "itself; point it at the actual transport "
                "(e.g. django.core.mail.backends.smtp.EmailBackend)."
            )

    # The base class's open/close are no-ops; we don't hold a persistent
    # connection because each background send creates its own backend.

    def send_messages(self, email_messages: Sequence[EmailMessage]) -> int:
        if not email_messages:
            return 0
        messages = list(email_messages)

        # Synchronous escape hatch for tests / debug.
        if getattr(settings, "ASYNC_EMAIL_SYNC", False) or getattr(
            settings, "TESTING", False
        ):
            _send_in_thread(
                self._real_backend_path, messages, self.fail_silently
            )
            return len(messages)

        executor = _get_executor()
        executor.submit(
            _send_in_thread,
            self._real_backend_path,
            messages,
            self.fail_silently,
        )
        return len(messages)

