"""Tests for apps.core.mail.AsyncEmailBackend."""
from __future__ import annotations

import threading
import time

from django.core import mail
from django.core.mail import EmailMessage, send_mail
from django.test import TestCase, override_settings


@override_settings(
    EMAIL_BACKEND="apps.core.mail.AsyncEmailBackend",
    ASYNC_EMAIL_REAL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ASYNC_EMAIL_SYNC=True,  # run inline so assertions are deterministic
)
class AsyncEmailBackendSyncTests(TestCase):
    """With ASYNC_EMAIL_SYNC=True the wrapper hands off inline."""

    def test_send_mail_delivers_to_real_backend(self):
        mail.outbox = []
        sent = send_mail(
            subject="Hello",
            message="Body",
            from_email="from@example.com",
            recipient_list=["to@example.com"],
        )
        self.assertEqual(sent, 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Hello")

    def test_empty_batch_is_noop(self):
        from apps.core.mail import AsyncEmailBackend

        self.assertEqual(AsyncEmailBackend().send_messages([]), 0)

    def test_rejects_recursive_backend(self):
        from apps.core.mail import AsyncEmailBackend

        with override_settings(
            ASYNC_EMAIL_REAL_BACKEND="apps.core.mail.AsyncEmailBackend"
        ):
            with self.assertRaises(ValueError):
                AsyncEmailBackend()


class _RecordingBackend:
    """Module-level backend that records calls + thread name."""

    calls: list[tuple[str, int]] = []

    def __init__(self, fail_silently=False):
        self.fail_silently = fail_silently

    def send_messages(self, messages):
        _RecordingBackend.calls.append(
            (threading.current_thread().name, len(messages))
        )
        return len(messages)


@override_settings(
    EMAIL_BACKEND="apps.core.mail.AsyncEmailBackend",
    ASYNC_EMAIL_REAL_BACKEND=(
        "apps.core.test_async_email._RecordingBackend"
    ),
    ASYNC_EMAIL_SYNC=False,
    TESTING=False,
)
class AsyncEmailBackendThreadTests(TestCase):
    """Verify the real transport runs on a background thread."""

    def setUp(self):
        _RecordingBackend.calls = []

    def test_send_runs_off_request_thread(self):
        from apps.core.mail import AsyncEmailBackend

        request_thread = threading.current_thread().name
        sent = AsyncEmailBackend().send_messages(
            [EmailMessage("s", "b", "f@x", ["t@x"])]
        )
        self.assertEqual(sent, 1)

        # Wait briefly for the worker to run.
        deadline = time.time() + 5
        while time.time() < deadline and not _RecordingBackend.calls:
            time.sleep(0.05)

        self.assertEqual(len(_RecordingBackend.calls), 1)
        worker_thread, count = _RecordingBackend.calls[0]
        self.assertEqual(count, 1)
        self.assertNotEqual(worker_thread, request_thread)
        self.assertTrue(worker_thread.startswith("async-email"))


class _BoomBackend:
    """Real backend that explodes — async wrapper must swallow it."""

    def __init__(self, fail_silently=False):
        pass

    def send_messages(self, messages):
        raise RuntimeError("smtp is on fire")


@override_settings(
    EMAIL_BACKEND="apps.core.mail.AsyncEmailBackend",
    ASYNC_EMAIL_REAL_BACKEND="apps.core.test_async_email._BoomBackend",
    ASYNC_EMAIL_SYNC=True,
)
class AsyncEmailBackendFailureTests(TestCase):
    def test_transport_failure_is_swallowed(self):
        # Must not raise — that's the whole point: request handlers keep
        # responding 200 even when the mail server is down.
        with self.assertLogs("apps.core.mail", level="ERROR") as cm:
            result = send_mail(
                "s", "b", "f@x", ["t@x"], fail_silently=False
            )
        self.assertEqual(result, 1)
        self.assertTrue(
            any("Async email send failed" in m for m in cm.output),
            cm.output,
        )

