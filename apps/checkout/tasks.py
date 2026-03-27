from celery import shared_task

from apps.checkout.emailing import send_tracking_links_email_for_order


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, retry_kwargs={"max_retries": 3})
def send_tracking_links_email_task(self, order_id: int, tracking_url: str, success_url: str) -> None:
    send_tracking_links_email_for_order(
        order_id=order_id,
        tracking_url=tracking_url,
        success_url=success_url,
    )


def enqueue_tracking_link_payloads(payloads: list[dict]) -> None:
    for payload in payloads:
        send_tracking_links_email_task.delay(
            payload["order_id"],
            payload["tracking_url"],
            payload["success_url"],
        )
