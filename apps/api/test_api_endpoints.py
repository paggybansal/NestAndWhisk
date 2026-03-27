import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from apps.orders.models import Order
from apps.subscriptions.models import SubscriptionPlan, UserSubscription


def _create_user(email: str):
    user_model = get_user_model()
    user = user_model(email=email)
    user.set_password("testpass123")
    user.save()
    return user


@pytest.mark.django_db
def test_public_subscription_plan_list_returns_active_plans_only():
    active_plan = SubscriptionPlan.objects.create(
        name="Weekly Ritual",
        slug="weekly-ritual",
        billing_interval=SubscriptionPlan.BillingInterval.WEEKLY,
        cadence_days=7,
        shipment_offset_days=3,
        box_size="6 cookies",
        price="24.00",
        is_active=True,
    )
    SubscriptionPlan.objects.create(
        name="Archived Plan",
        slug="archived-plan",
        billing_interval=SubscriptionPlan.BillingInterval.MONTHLY,
        cadence_days=30,
        shipment_offset_days=15,
        box_size="12 cookies",
        price="44.00",
        is_active=False,
    )

    client = APIClient()
    response = client.get(reverse("api:subscription-plan-list"))

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["results"][0]["slug"] == active_plan.slug


@pytest.mark.django_db
def test_public_subscription_plan_detail_returns_only_active_plans():
    active_plan = SubscriptionPlan.objects.create(
        name="Weekly Ritual",
        slug="weekly-ritual",
        billing_interval=SubscriptionPlan.BillingInterval.WEEKLY,
        cadence_days=7,
        shipment_offset_days=3,
        box_size="6 cookies",
        price="24.00",
        is_active=True,
    )
    inactive_plan = SubscriptionPlan.objects.create(
        name="Hidden Ritual",
        slug="hidden-ritual",
        billing_interval=SubscriptionPlan.BillingInterval.MONTHLY,
        cadence_days=30,
        shipment_offset_days=15,
        box_size="12 cookies",
        price="54.00",
        is_active=False,
    )

    client = APIClient()
    active_response = client.get(
        reverse("api:subscription-plan-detail", kwargs={"slug": active_plan.slug})
    )
    inactive_response = client.get(
        reverse("api:subscription-plan-detail", kwargs={"slug": inactive_plan.slug})
    )

    assert active_response.status_code == 200
    assert active_response.json()["slug"] == active_plan.slug
    assert inactive_response.status_code == 404


@pytest.mark.django_db
def test_public_subscription_plan_list_supports_filtering_ordering_and_page_size():
    SubscriptionPlan.objects.create(
        name="Weekly Ritual",
        slug="weekly-ritual",
        headline="Chocolate-forward weekly box",
        billing_interval=SubscriptionPlan.BillingInterval.WEEKLY,
        cadence_days=7,
        shipment_offset_days=3,
        box_size="6 cookies",
        price="24.00",
        is_featured=True,
        is_active=True,
    )
    highest_priced = SubscriptionPlan.objects.create(
        name="Grand Gifting Ritual",
        slug="grand-gifting-ritual",
        headline="Chocolate gifting centerpiece",
        billing_interval=SubscriptionPlan.BillingInterval.MONTHLY,
        cadence_days=30,
        shipment_offset_days=15,
        box_size="24 cookies",
        price="78.00",
        is_featured=True,
        is_active=True,
    )
    SubscriptionPlan.objects.create(
        name="Not Featured",
        slug="not-featured",
        headline="Savory profile",
        billing_interval=SubscriptionPlan.BillingInterval.BIWEEKLY,
        cadence_days=14,
        shipment_offset_days=7,
        box_size="8 cookies",
        price="34.00",
        is_featured=False,
        is_active=True,
    )

    client = APIClient()
    response = client.get(
        reverse("api:subscription-plan-list"),
        {"is_featured": True, "ordering": "-price", "page_size": 1, "search": "chocolate"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 2
    assert len(payload["results"]) == 1
    assert payload["results"][0]["slug"] == highest_priced.slug
    assert payload["next"] is not None


@pytest.mark.django_db
def test_my_subscriptions_requires_authentication():
    client = APIClient()
    response = client.get(reverse("api:my-subscriptions"))
    assert response.status_code in {401, 403}


@pytest.mark.django_db
def test_my_subscriptions_returns_only_current_users_subscriptions():
    user = _create_user("member@example.com")
    other_user = _create_user("other@example.com")
    plan = SubscriptionPlan.objects.create(
        name="Monthly Ritual",
        slug="monthly-ritual",
        billing_interval=SubscriptionPlan.BillingInterval.MONTHLY,
        cadence_days=30,
        shipment_offset_days=15,
        box_size="12 cookies",
        price="44.00",
        is_active=True,
    )
    UserSubscription.objects.create(user=user, plan=plan, renewal_day=5)
    UserSubscription.objects.create(user=other_user, plan=plan, renewal_day=9)

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get(reverse("api:my-subscriptions"))

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["results"][0]["renewal_day"] == 5


@pytest.mark.django_db
def test_my_subscriptions_supports_search_ordering_and_pagination():
    user = _create_user("member-search@example.com")
    weekly_plan = SubscriptionPlan.objects.create(
        name="Weekly Ritual",
        slug="weekly-ritual",
        headline="Cookie cadence",
        billing_interval=SubscriptionPlan.BillingInterval.WEEKLY,
        cadence_days=7,
        shipment_offset_days=3,
        box_size="6 cookies",
        price="24.00",
        is_active=True,
    )
    monthly_plan = SubscriptionPlan.objects.create(
        name="Monthly Gifting Club",
        slug="monthly-gifting-club",
        headline="Gift-worthy chocolate assortment",
        billing_interval=SubscriptionPlan.BillingInterval.MONTHLY,
        cadence_days=30,
        shipment_offset_days=15,
        box_size="12 cookies",
        price="44.00",
        is_active=True,
    )
    UserSubscription.objects.create(
        user=user,
        plan=weekly_plan,
        renewal_day=4,
        next_renewal_date="2026-03-04",
        next_shipment_date="2026-03-07",
    )
    matching_subscription = UserSubscription.objects.create(
        user=user,
        plan=monthly_plan,
        renewal_day=18,
        next_renewal_date="2026-03-18",
        next_shipment_date="2026-04-02",
    )

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get(
        reverse("api:my-subscriptions"),
        {"search": "gift", "ordering": "next_renewal_date", "page_size": 1},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert len(payload["results"]) == 1
    assert payload["results"][0]["id"] == matching_subscription.pk
    assert payload["results"][0]["plan"]["slug"] == monthly_plan.slug


@pytest.mark.django_db
def test_my_orders_supports_status_filtering():
    user = _create_user("orders@example.com")
    Order.objects.create(
        user=user,
        customer_email=user.email,
        customer_first_name="Nest",
        shipping_address_line_1="123 Baker Street",
        shipping_city="Delhi",
        shipping_state="Delhi",
        shipping_postal_code="110001",
        shipping_country="India",
        status=Order.Status.PAID,
        payment_status=Order.PaymentStatus.PAID,
        subtotal="30.00",
        total="30.00",
    )
    Order.objects.create(
        user=user,
        customer_email=user.email,
        customer_first_name="Nest",
        shipping_address_line_1="123 Baker Street",
        shipping_city="Delhi",
        shipping_state="Delhi",
        shipping_postal_code="110001",
        shipping_country="India",
        status=Order.Status.CANCELLED,
        payment_status=Order.PaymentStatus.UNPAID,
        subtotal="18.00",
        total="18.00",
    )

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get(reverse("api:my-orders"), {"status": Order.Status.PAID})

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["results"][0]["status"] == Order.Status.PAID


@pytest.mark.django_db
def test_my_orders_support_search_ordering_and_user_scoping():
    user = _create_user("orders-search@example.com")
    other_user = _create_user("other-orders@example.com")
    lower_total = Order.objects.create(
        user=user,
        customer_email=user.email,
        customer_first_name="Nest",
        shipping_address_line_1="123 Baker Street",
        shipping_city="Delhi",
        shipping_state="Delhi",
        shipping_postal_code="110001",
        shipping_country="India",
        status=Order.Status.PENDING,
        payment_status=Order.PaymentStatus.UNPAID,
        subtotal="18.00",
        total="18.00",
    )
    higher_total = Order.objects.create(
        user=user,
        customer_email=user.email,
        customer_first_name="Nest",
        shipping_address_line_1="456 Pastry Lane",
        shipping_city="Delhi",
        shipping_state="Delhi",
        shipping_postal_code="110002",
        shipping_country="India",
        status=Order.Status.PAID,
        payment_status=Order.PaymentStatus.PAID,
        subtotal="52.00",
        total="52.00",
    )
    Order.objects.create(
        user=other_user,
        customer_email=other_user.email,
        customer_first_name="Other",
        shipping_address_line_1="789 Cookie Road",
        shipping_city="Mumbai",
        shipping_state="Maharashtra",
        shipping_postal_code="400001",
        shipping_country="India",
        status=Order.Status.PAID,
        payment_status=Order.PaymentStatus.PAID,
        subtotal="82.00",
        total="82.00",
    )

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get(reverse("api:my-orders"), {"ordering": "-total", "page_size": 2})

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 2
    assert [result["order_number"] for result in payload["results"]] == [
        higher_total.order_number,
        lower_total.order_number,
    ]


