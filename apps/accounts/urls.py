from django.urls import path

from apps.accounts.views import (
    AccountOrdersView,
    CustomerLoginView,
    CustomerPasswordResetView,
    CustomerSignupView,
    DashboardView,
    ProfileUpdateView,
)


urlpatterns = [
    path("dashboard/", DashboardView.as_view(), name="account_dashboard"),
    path("orders/", AccountOrdersView.as_view(), name="account_orders"),
    path("profile/", ProfileUpdateView.as_view(), name="account_profile"),
    path("login/", CustomerLoginView.as_view(), name="account_login"),
    path("signup/", CustomerSignupView.as_view(), name="account_signup"),
    path("password/reset/", CustomerPasswordResetView.as_view(), name="account_reset_password"),
]
