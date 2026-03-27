from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse

from apps.core.models import TimeStampedModel
from apps.orders.models import Order


class SubscriptionPlan(TimeStampedModel):
    class BillingInterval(models.TextChoices):
        WEEKLY = "weekly", "Weekly"
        BIWEEKLY = "biweekly", "Biweekly"
        MONTHLY = "monthly", "Monthly"

    name = models.CharField(max_length=140)
    slug = models.SlugField(max_length=160, unique=True)
    headline = models.CharField(max_length=180, blank=True)
    description = models.TextField(blank=True)
    billing_interval = models.CharField(max_length=20, choices=BillingInterval.choices)
    cadence_days = models.PositiveSmallIntegerField(default=30)
    shipment_offset_days = models.PositiveSmallIntegerField(default=15)
    box_size = models.CharField(max_length=80)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    compare_at_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    stripe_price_id = models.CharField(max_length=120, blank=True)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]
        indexes = [models.Index(fields=["billing_interval", "is_active"])]

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self):
        return reverse("subscriptions:detail", kwargs={"slug": self.slug})

    def save(self, *args, **kwargs):
        cadence_defaults = {
            self.BillingInterval.WEEKLY: (7, 3),
            self.BillingInterval.BIWEEKLY: (14, 7),
            self.BillingInterval.MONTHLY: (30, 15),
        }
        default_cadence_days, default_shipment_offset = cadence_defaults.get(self.billing_interval, (30, 15))
        if not self.cadence_days:
            self.cadence_days = default_cadence_days
        if not self.shipment_offset_days:
            self.shipment_offset_days = default_shipment_offset
        super().save(*args, **kwargs)

    def calculate_schedule(self, *, renewal_day: int, from_date: date | None = None) -> tuple[date, date]:
        anchor_date = from_date or date.today()
        renewal_anchor = anchor_date.replace(day=min(renewal_day, 28))
        if renewal_anchor < anchor_date:
            if anchor_date.month == 12:
                renewal_anchor = renewal_anchor.replace(year=anchor_date.year + 1, month=1)
            else:
                renewal_anchor = renewal_anchor.replace(month=anchor_date.month + 1)
        shipment_date = renewal_anchor + timedelta(days=self.shipment_offset_days)
        return renewal_anchor, shipment_date


class UserSubscription(TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        CANCELLED = "cancelled", "Cancelled"
        PAST_DUE = "past_due", "Past due"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name="subscriptions",
    )
    latest_order = models.ForeignKey(
        Order,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subscription_records",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    stripe_subscription_id = models.CharField(max_length=120, blank=True)
    stripe_customer_id = models.CharField(max_length=120, blank=True)
    flavor_preferences = models.JSONField(default=list, blank=True)
    renewal_day = models.PositiveSmallIntegerField(default=1)
    next_renewal_date = models.DateField(null=True, blank=True)
    next_shipment_date = models.DateField(null=True, blank=True)
    paused_from = models.DateField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    admin_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "next_renewal_date"]),
            models.Index(fields=["status", "next_shipment_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.user.email} · {self.plan.name}"

    def refresh_schedule(self, *, from_date: date | None = None) -> None:
        self.next_renewal_date, self.next_shipment_date = self.plan.calculate_schedule(
            renewal_day=self.renewal_day,
            from_date=from_date,
        )


class SubscriptionShipment(TimeStampedModel):
    class ShipmentStatus(models.TextChoices):
        UPCOMING = "upcoming", "Upcoming"
        PROCESSING = "processing", "Processing"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"
        SKIPPED = "skipped", "Skipped"

    subscription = models.ForeignKey(
        UserSubscription,
        on_delete=models.CASCADE,
        related_name="shipments",
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subscription_shipments",
    )
    scheduled_for = models.DateField()
    status = models.CharField(max_length=20, choices=ShipmentStatus.choices, default=ShipmentStatus.UPCOMING)
    tracking_reference = models.CharField(max_length=120, blank=True)
    shipment_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["scheduled_for"]
        indexes = [models.Index(fields=["status", "scheduled_for"])]

    def __str__(self) -> str:
        return f"{self.subscription} · {self.scheduled_for}"
