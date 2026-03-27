from __future__ import annotations

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from config.settings.base import env


class Command(BaseCommand):
    help = "Create or refresh a local admin user for Nest & Whisk."

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            default=env("DJANGO_SUPERUSER_EMAIL", default="admin@nestandwhisk.com"),
            help="Email address for the admin user.",
        )
        parser.add_argument(
            "--password",
            default=env("DJANGO_SUPERUSER_PASSWORD", default="ChangeMe123!"),
            help="Password for the admin user.",
        )
        parser.add_argument("--first-name", default="Nest")
        parser.add_argument("--last-name", default="Admin")

    def handle(self, *args, **options):
        email = (options["email"] or "").strip().lower()
        password = options["password"] or ""
        first_name = options["first_name"].strip()
        last_name = options["last_name"].strip()

        if not email:
            raise CommandError("An admin email address is required.")
        if len(password) < 8:
            raise CommandError("Choose a password with at least 8 characters.")

        User = get_user_model()
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "first_name": first_name,
                "last_name": last_name,
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
            },
        )

        user.first_name = first_name or user.first_name
        user.last_name = last_name or user.last_name
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.set_password(password)
        user.save()

        action = "Created" if created else "Updated"
        admin_url = f"/{settings.ADMIN_URL}login/"
        self.stdout.write(self.style.SUCCESS(f"{action} admin user: {email}"))
        self.stdout.write(f"Admin login URL: {admin_url}")

