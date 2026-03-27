from django.urls import path

from apps.subscriptions.views import (
    SubscriptionCancelView,
    SubscriptionDashboardView,
    SubscriptionPauseView,
    SubscriptionPlanDetailView,
    SubscriptionPlanListView,
    SubscriptionPreferencesUpdateView,
    SubscriptionResumeView,
    SubscriptionSignupView,
)

app_name = "subscriptions"

urlpatterns = [
    path("", SubscriptionPlanListView.as_view(), name="list"),
    path("dashboard/", SubscriptionDashboardView.as_view(), name="dashboard"),
    path("dashboard/signup/", SubscriptionSignupView.as_view(), name="signup"),
    path("dashboard/<int:pk>/preferences/", SubscriptionPreferencesUpdateView.as_view(), name="preferences"),
    path("dashboard/<int:pk>/pause/", SubscriptionPauseView.as_view(), name="pause"),
    path("dashboard/<int:pk>/resume/", SubscriptionResumeView.as_view(), name="resume"),
    path("dashboard/<int:pk>/cancel/", SubscriptionCancelView.as_view(), name="cancel"),
    path("<slug:slug>/", SubscriptionPlanDetailView.as_view(), name="detail"),
]
