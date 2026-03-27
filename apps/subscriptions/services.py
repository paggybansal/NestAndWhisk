from datetime import date

from django.db.models import Q

from apps.subscriptions.models import SubscriptionShipment, UserSubscription


def refresh_due_subscription_schedules(*, on_date: date | None = None) -> int:
    reference_date = on_date or date.today()
    subscriptions = UserSubscription.objects.select_related("plan").filter(
        status=UserSubscription.Status.ACTIVE,
    ).filter(
        Q(next_renewal_date__isnull=True)
        | Q(next_renewal_date__lte=reference_date)
        | Q(next_shipment_date__isnull=True)
        | Q(next_shipment_date__lte=reference_date)
    )

    updated = 0
    for subscription in subscriptions:
        previous_renewal = subscription.next_renewal_date
        previous_shipment = subscription.next_shipment_date
        subscription.refresh_schedule(from_date=reference_date)
        if (
            subscription.next_renewal_date != previous_renewal
            or subscription.next_shipment_date != previous_shipment
        ):
            subscription.save(
                update_fields=["next_renewal_date", "next_shipment_date", "updated_at"]
            )
            updated += 1

    return updated


def create_upcoming_subscription_shipments(*, on_date: date | None = None) -> int:
    reference_date = on_date or date.today()
    subscriptions = UserSubscription.objects.select_related("plan").filter(
        status=UserSubscription.Status.ACTIVE,
        next_shipment_date__isnull=False,
        next_shipment_date__lte=reference_date,
    )

    created = 0
    for subscription in subscriptions:
        shipment_exists = SubscriptionShipment.objects.filter(
            subscription=subscription,
            scheduled_for=subscription.next_shipment_date
        ).exists()
        if shipment_exists:
            continue

        SubscriptionShipment.objects.create(
            subscription=subscription,
            scheduled_for=subscription.next_shipment_date,
            status=SubscriptionShipment.ShipmentStatus.UPCOMING,
        )
        created += 1

    return created


