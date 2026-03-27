from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import F

from apps.orders.models import Order, Payment


class Command(BaseCommand):
    help = "Normalize legacy Order and Payment currency values to a single target currency."

    def add_arguments(self, parser):
        parser.add_argument(
            "--currency",
            default="INR",
            help="Target uppercase currency code to store on Order and Payment rows (default: INR).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview the rows that would be updated without writing changes.",
        )

    def handle(self, *args, **options):
        target_currency = options["currency"].strip().upper() or "INR"
        dry_run = options["dry_run"]

        order_qs = Order.objects.exclude(currency=target_currency)
        payment_qs = Payment.objects.exclude(currency=target_currency)

        order_count = order_qs.count()
        payment_count = payment_qs.count()

        self.stdout.write(self.style.NOTICE(f"Target currency: {target_currency}"))
        self.stdout.write(f"Orders needing normalization: {order_count}")
        self.stdout.write(f"Payments needing normalization: {payment_count}")

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run only. No database rows were changed."))
            return

        with transaction.atomic():
            updated_orders = order_qs.update(currency=target_currency)
            updated_payments = payment_qs.update(currency=target_currency)

        remaining_orders = Order.objects.exclude(currency=target_currency).count()
        remaining_payments = Payment.objects.exclude(currency=target_currency).count()
        mismatched_payment_order_pairs = Payment.objects.exclude(currency=F("order__currency")).count()

        self.stdout.write(self.style.SUCCESS(f"Updated orders: {updated_orders}"))
        self.stdout.write(self.style.SUCCESS(f"Updated payments: {updated_payments}"))
        self.stdout.write(f"Remaining non-{target_currency} orders: {remaining_orders}")
        self.stdout.write(f"Remaining non-{target_currency} payments: {remaining_payments}")
        self.stdout.write(f"Payment/order currency mismatches: {mismatched_payment_order_pairs}")

