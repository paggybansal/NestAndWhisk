from apps.subscriptions.tasks import (
    create_subscription_shipments_task,
    refresh_subscription_schedules_task,
)


def test_refresh_subscription_schedules_task_delegates_to_service(monkeypatch):
    captured = {}

    def fake_refresh():
        captured["called"] = True
        return 7

    monkeypatch.setattr("apps.subscriptions.tasks.refresh_due_subscription_schedules", fake_refresh)

    result = refresh_subscription_schedules_task.run()

    assert captured["called"] is True
    assert result == 7



def test_create_subscription_shipments_task_delegates_to_service(monkeypatch):
    captured = {}

    def fake_create():
        captured["called"] = True
        return 3

    monkeypatch.setattr("apps.subscriptions.tasks.create_upcoming_subscription_shipments", fake_create)

    result = create_subscription_shipments_task.run()

    assert captured["called"] is True
    assert result == 3

