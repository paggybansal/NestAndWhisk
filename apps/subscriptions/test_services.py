from datetime import date

import pytest
from django.contrib.auth import get_user_model

from apps.subscriptions.models import SubscriptionPlan, SubscriptionShipment, UserSubscription
from apps.subscriptions.services import (
    create_upcoming_subscription_shipments,
    refresh_due_subscription_schedules,
)


def _create_user(email: str):
    user_model = get_user_model()
    user = user_model(email=email)
    user.set_password("testpass123")
    user.save()
    return user


@pytest.mark.django_db
def test_refresh_due_subscription_schedules_updates_only_active_due_or_unscheduled_subscriptions():
    user = _create_user("subscriber@example.com")
    plan = SubscriptionPlan.objects.create(
        name="Weekly Ritual",
        slug="weekly-ritual",
        billing_interval=SubscriptionPlan.BillingInterval.WEEKLY,
        cadence_days=7,
        shipment_offset_days=3,
        box_size="6 cookies",
        price="24.00",
        is_active=True,
    )
    due_subscription = UserSubscription.objects.create(
        user=user,
        plan=plan,
        status=UserSubscription.Status.ACTIVE,
        renewal_day=5,
        next_renewal_date=date(2026, 3, 1),
        next_shipment_date=date(2026, 3, 4),
    )
    unscheduled_subscription = UserSubscription.objects.create(
        user=user,
        plan=plan,
        status=UserSubscription.Status.ACTIVE,
        renewal_day=10,
        next_renewal_date=None,
        next_shipment_date=None,
    )
    future_subscription = UserSubscription.objects.create(
        user=user,
        plan=plan,
        status=UserSubscription.Status.ACTIVE,
        renewal_day=22,
        next_renewal_date=date(2026, 4, 22),
        next_shipment_date=date(2026, 4, 25),
    )
    paused_subscription = UserSubscription.objects.create(
        user=user,
        plan=plan,
        status=UserSubscription.Status.PAUSED,
        renewal_day=8,
        next_renewal_date=date(2026, 3, 2),
        next_shipment_date=date(2026, 3, 5),
    )

    updated = refresh_due_subscription_schedules(on_date=date(2026, 3, 18))

    due_subscription.refresh_from_db()
    unscheduled_subscription.refresh_from_db()
    future_subscription.refresh_from_db()
    paused_subscription.refresh_from_db()

    assert updated == 2
    assert due_subscription.next_renewal_date == date(2026, 4, 5)
    assert due_subscription.next_shipment_date == date(2026, 4, 8)
    assert unscheduled_subscription.next_renewal_date == date(2026, 4, 10)
    assert unscheduled_subscription.next_shipment_date == date(2026, 4, 13)
    assert future_subscription.next_renewal_date == date(2026, 4, 22)
    assert paused_subscription.next_renewal_date == date(2026, 3, 2)


@pytest.mark.django_db
def test_create_upcoming_subscription_shipments_is_idempotent_and_active_only():
    user = _create_user("shipments@example.com")
    plan = SubscriptionPlan.objects.create(
        name="Monthly Gifting Club",
        slug="monthly-gifting-club",
        billing_interval=SubscriptionPlan.BillingInterval.MONTHLY,
        cadence_days=30,
        shipment_offset_days=15,
        box_size="12 cookies",
        price="44.00",
        is_active=True,
    )
    due_subscription = UserSubscription.objects.create(
        user=user,
        plan=plan,
        status=UserSubscription.Status.ACTIVE,
        renewal_day=2,
        next_renewal_date=date(2026, 3, 2),
        next_shipment_date=date(2026, 3, 17),
    )
    UserSubscription.objects.create(
        user=user,
        plan=plan,
        status=UserSubscription.Status.PAUSED,
        renewal_day=4,
        next_renewal_date=date(2026, 3, 4),
        next_shipment_date=date(2026, 3, 17),
    )
    UserSubscription.objects.create(
        user=user,
        plan=plan,
        status=UserSubscription.Status.ACTIVE,
        renewal_day=20,
        next_renewal_date=date(2026, 3, 20),
        next_shipment_date=date(2026, 4, 4),
    )

    created = create_upcoming_subscription_shipments(on_date=date(2026, 3, 18))
    duplicate_run = create_upcoming_subscription_shipments(on_date=date(2026, 3, 18))

    assert created == 1
    assert duplicate_run == 0
    shipment = SubscriptionShipment.objects.get(subscription=due_subscription)
    assert shipment.scheduled_for == date(2026, 3, 17)
    assert shipment.status == SubscriptionShipment.ShipmentStatus.UPCOMING
    assert SubscriptionShipment.objects.count() == 1

