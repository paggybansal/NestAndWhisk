from html import unescape

import pytest
from allauth.account.models import EmailAddress
from allauth.account.middleware import AccountMiddleware
from django.http import HttpResponse
from django.contrib.auth.models import AnonymousUser
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.urls import resolve, reverse

from apps.core.branding import get_brand_logo_path
from apps.orders.models import Order
from apps.subscriptions.models import SubscriptionPlan


def _create_user(email: str, **extra_fields):
    user_model = get_user_model()
    user = user_model(email=email, **extra_fields)
    user.set_password("testpass123")
    user.save()
    return user


def render_path(path, *, user=None):
    factory = RequestFactory()
    request = factory.get(path, HTTP_HOST="127.0.0.1")
    SessionMiddleware(lambda req: HttpResponse()).process_request(request)
    request.session.save()
    request.user = user or AnonymousUser()
    setattr(request, "_messages", FallbackStorage(request))
    match = resolve(path)
    wrapped_view = AccountMiddleware(
        lambda req: match.func(req, *match.args, **match.kwargs)
    )
    response = wrapped_view(request)
    if hasattr(response, "render"):
        response = response.render()
    return response


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("route_name", "expected_path"),
    [
        ("account_login", "/account/login/"),
        ("account_signup", "/account/signup/"),
        ("account_reset_password", "/account/password/reset/"),
        ("account_orders", "/account/orders/"),
        ("account_email", "/account/email/"),
        ("account_change_password", "/account/password/change/"),
        ("account_logout", "/account/logout/"),
    ],
)
def test_canonical_account_routes_live_under_account_prefix(route_name, expected_path):
    assert reverse(route_name) == expected_path


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("legacy_path", "expected_target"),
    [
        ("/accounts/", "/account/login/"),
        ("/accounts/login/", "/account/login/"),
        ("/accounts/signup/", "/account/signup/"),
        ("/accounts/password/reset/", "/account/password/reset/"),
        ("/accounts/email/", "/account/email/"),
        ("/accounts/password/change/", "/account/password/change/"),
        ("/accounts/logout/", "/account/logout/"),
    ],
)
def test_legacy_accounts_paths_redirect_to_canonical_account_prefix(client, legacy_path, expected_target):
    response = client.get(legacy_path, follow=False)

    assert response.status_code == 301
    assert response["Location"].endswith(expected_target)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("path", "expected_copy"),
    [
        ("/account/login/", "Welcome back."),
        ("/account/signup/", "Join the Nest & Whisk table."),
        ("/account/password/reset/", "Reset your password."),
    ],
)
def test_public_auth_pages_render_with_branding_and_shared_base_context(client, path, expected_copy):
    response = render_path(path)
    content = unescape(response.content.decode())
    brand_logo_path = get_brand_logo_path()

    assert response.status_code == 200
    assert "Nest & Whisk" in content
    assert brand_logo_path in content
    assert '/static/brand/favicon-32x32.png' in content
    assert '/static/brand/apple-touch-icon.png' in content
    assert '/static/brand/site.webmanifest' in content
    assert content.count(brand_logo_path) >= 3
    assert expected_copy in content
    assert "Free nationwide shipping on curated gift boxes over ₹2,500." in content
    assert "Join the list" in content


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("route_name", "expected_copy"),
    [
        ("account_email", "Manage your email address."),
        ("account_change_password", "Change your password."),
    ],
)
def test_authenticated_allauth_account_pages_render_with_shared_base_context(client, route_name, expected_copy):
    email = "member@example.com"
    user = _create_user(email, first_name="Nest")
    EmailAddress.objects.create(user=user, email=email, primary=True, verified=True)

    response = render_path(reverse(route_name), user=user)
    content = unescape(response.content.decode())
    brand_logo_path = get_brand_logo_path()

    assert response.status_code == 200
    assert expected_copy in content
    assert "Nest & Whisk" in content
    assert brand_logo_path in content
    assert '/static/brand/favicon-32x32.png' in content
    assert '/static/brand/apple-touch-icon.png' in content
    assert '/static/brand/site.webmanifest' in content
    assert content.count(brand_logo_path) >= 3
    assert "Free nationwide shipping on curated gift boxes over ₹2,500." in content
    assert "Join the list" in content


@pytest.mark.django_db
def test_dashboard_renders_signout_as_post_form(client):
    user = _create_user("dashboard@example.com", first_name="Nest")
    client.force_login(user)

    response = client.get(reverse("account_dashboard"))
    content = unescape(response.content.decode())

    assert response.status_code == 200
    assert '<form method="post" action="/account/logout/">' in content
    assert 'csrfmiddlewaretoken' in content
    assert 'href="/account/logout/"' not in content
    assert 'href="/account/orders/"' in content
    assert 'href="/subscriptions/dashboard/"' in content
    assert 'href="/account/profile/"' in content


@pytest.mark.django_db
def test_dashboard_link_targets_load_for_authenticated_user(client):
    user = _create_user("links@example.com", first_name="Nest")
    SubscriptionPlan.objects.create(
        name="Monthly Cookie Ritual",
        slug="monthly-cookie-ritual",
        headline="A monthly box of bestsellers.",
        description="Seasonal bakes delivered every month.",
        billing_interval=SubscriptionPlan.BillingInterval.MONTHLY,
        box_size="12 cookies",
        price="1899.00",
    )
    client.force_login(user)

    orders_response = client.get(reverse("account_orders"))
    profile_response = client.get(reverse("account_profile"))
    subscriptions_response = client.get(reverse("subscriptions:dashboard"))

    assert orders_response.status_code == 200
    assert profile_response.status_code == 200
    assert subscriptions_response.status_code == 200
    assert "Your Nest & Whisk orders." in unescape(orders_response.content.decode())
    assert "Update your account details." in unescape(profile_response.content.decode())
    assert "Your recurring cookie ritual." in unescape(subscriptions_response.content.decode())


@pytest.mark.django_db
def test_account_orders_page_renders_signed_in_user_orders(client):
    user = _create_user("orders@example.com", first_name="Nest")
    order = Order.objects.create(
        user=user,
        customer_email=user.email,
        customer_first_name="Nest",
        customer_last_name="Guest",
        shipping_address_line_1="123 Baker Street",
        shipping_city="Delhi",
        shipping_state="Delhi",
        shipping_postal_code="110001",
        shipping_country="India",
        subtotal="2499.50",
        total="2499.50",
    )

    client.force_login(user)
    response = client.get(reverse("account_orders"))
    content = unescape(response.content.decode())

    assert response.status_code == 200
    assert "Your Nest & Whisk orders." in content
    assert "Order archive" in content
    assert order.order_number in content
    assert 'href="/checkout/success/' in content
    assert 'href="/checkout/track/' in content


@pytest.mark.django_db
def test_logout_post_signs_user_out_and_redirects_home(client):
    user = _create_user("logout@example.com", first_name="Nest")
    client.force_login(user)

    response = client.post(reverse("account_logout"), follow=False)

    assert response.status_code == 302
    assert response["Location"] == reverse("home")
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_logout_page_renders_with_branding_for_authenticated_user(client):
    email = "logout-page@example.com"
    user = _create_user(email, first_name="Nest")
    EmailAddress.objects.create(user=user, email=email, primary=True, verified=True)

    response = render_path(reverse("account_logout"), user=user)
    content = unescape(response.content.decode())

    assert response.status_code == 200
    assert "Nest & Whisk" in content
    assert "Sign out of your account?" in content
    assert '<form method="post" action="/account/logout/"' in content
    assert 'csrfmiddlewaretoken' in content
    assert get_brand_logo_path() in content


