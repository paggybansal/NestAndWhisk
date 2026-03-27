import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from html import unescape

from apps.core.branding import get_brand_logo_path


@pytest.mark.django_db
@pytest.mark.parametrize(
    "route_name",
    [
        "admin:index",
        "admin:catalog_product_changelist",
        "admin:cart_cart_changelist",
        "admin:reviews_review_changelist",
    ],
)
def test_admin_changelists_render_for_superuser(client, route_name):
    user_model = get_user_model()
    admin_user = user_model(
        email="admin-render@example.com",
        is_staff=True,
        is_superuser=True,
    )
    admin_user.set_password("testpass123")
    admin_user.save()

    client.force_login(admin_user)
    response = client.get(reverse(route_name))
    content = unescape(response.content.decode())

    assert response.status_code == 200
    assert "Nest & Whisk Admin" in content
    assert get_brand_logo_path() in content
    assert "/static/admin/nest_and_whisk_admin.css" in content
    assert "Managed with warmth, precision, and a baker’s eye for detail." in content


@pytest.mark.django_db
def test_admin_login_page_uses_nest_and_whisk_branding(client):
    response = client.get(reverse("admin:login"))
    content = unescape(response.content.decode())

    assert response.status_code == 200
    assert "Welcome back to the bakery studio." in content
    assert get_brand_logo_path() in content
    assert "/static/admin/nest_and_whisk_admin.css" in content
    assert "Admin sign in" in content


