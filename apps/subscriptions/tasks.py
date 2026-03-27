from celery import shared_task

from apps.subscriptions.services import (
    create_upcoming_subscription_shipments,
    refresh_due_subscription_schedules,
)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, retry_kwargs={"max_retries": 3})
def refresh_subscription_schedules_task(self) -> int:
    return refresh_due_subscription_schedules()


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, retry_kwargs={"max_retries": 3})
def create_subscription_shipments_task(self) -> int:
    return create_upcoming_subscription_shipments()

