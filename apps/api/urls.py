from django.urls import path

from apps.api.views import (
    MyOrderListAPIView,
    MySubscriptionListAPIView,
    SubscriptionPlanDetailAPIView,
    SubscriptionPlanListAPIView,
)

app_name = "api"

urlpatterns = [
    path("subscriptions/plans/", SubscriptionPlanListAPIView.as_view(), name="subscription-plan-list"),
    path("subscriptions/plans/<slug:slug>/", SubscriptionPlanDetailAPIView.as_view(), name="subscription-plan-detail"),
    path("me/subscriptions/", MySubscriptionListAPIView.as_view(), name="my-subscriptions"),
    path("me/orders/", MyOrderListAPIView.as_view(), name="my-orders"),
]

