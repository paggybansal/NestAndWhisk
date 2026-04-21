"""
Send a one-off test email via the configured EMAIL_BACKEND.

Usage (locally with Railway env loaded):
    railway run python manage.py test_email you@example.com

Exits non-zero if the send fails, so it's safe to chain in a deploy check.
"""

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Send a test email to verify EMAIL_BACKEND configuration."

    def add_arguments(self, parser):
        parser.add_argument("to", help="Destination email address")
        parser.add_argument(
            "--subject",
            default="Nest & Whisk test email",
            help="Email subject line (default: %(default)s)",
        )

    def handle(self, *args, **options):
        to_addr = options["to"]
        subject = options["subject"]
        self.stdout.write(f"backend:       {settings.EMAIL_BACKEND}")
        self.stdout.write(f"host:          {settings.EMAIL_HOST or '(none — using backend default)'}")
        self.stdout.write(f"from:          {settings.DEFAULT_FROM_EMAIL}")
        self.stdout.write(f"to:            {to_addr}")
        self.stdout.write(f"timeout (s):   {getattr(settings, 'EMAIL_TIMEOUT', 'default')}")
        try:
            sent = send_mail(
                subject=subject,
                message=(
                    "If you received this, the Nest & Whisk email pipeline is wired "
                    "correctly.\n\n"
                    "You can safely delete this message."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to_addr],
                fail_silently=False,
            )
        except Exception as exc:  # noqa: BLE001 — surface the real error
            raise CommandError(f"send failed: {exc!r}") from exc
        if sent != 1:
            raise CommandError(f"send_mail returned {sent}; expected 1")
        self.stdout.write(self.style.SUCCESS("sent OK"))

