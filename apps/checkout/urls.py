from django.urls import path

from apps.checkout.views import (
    CheckoutCancelledView,
    DeliveryEstimateLookupView,
    MockPaymentView,
    CheckoutStartPaymentView,
    CheckoutSuccessView,
    CheckoutView,
    OrderLookupView,
    OrderTrackingView,
    StripeWebhookView,
    TrackingLinkRequestView,
)

app_name = "checkout"

urlpatterns = [
    path("", CheckoutView.as_view(), name="index"),
    path("delivery-lookup/", DeliveryEstimateLookupView.as_view(), name="delivery_lookup"),
    path("success/<str:order_number>/", CheckoutSuccessView.as_view(), name="success"),
    path("cancelled/<str:order_number>/", CheckoutCancelledView.as_view(), name="cancelled"),
    path("pay/<str:order_number>/", CheckoutStartPaymentView.as_view(), name="start_payment"),
    path("mock/<str:order_number>/", MockPaymentView.as_view(), name="mock_payment"),
    path("track/", OrderLookupView.as_view(), name="lookup"),
    path("track/send-links/", TrackingLinkRequestView.as_view(), name="send_tracking_links"),
    path("track/<str:order_number>/", OrderTrackingView.as_view(), name="tracking"),
    path("webhooks/stripe/", StripeWebhookView.as_view(), name="stripe_webhook"),
]
