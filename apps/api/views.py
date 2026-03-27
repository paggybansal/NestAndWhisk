from rest_framework import generics, pagination, permissions

from apps.api.serializers import OrderSerializer, SubscriptionPlanSerializer, UserSubscriptionSerializer
from apps.orders.models import Order
from apps.subscriptions.models import SubscriptionPlan, UserSubscription


class DefaultPageNumberPagination(pagination.PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50


class SubscriptionPlanListAPIView(generics.ListAPIView):
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = DefaultPageNumberPagination
    filterset_fields = ["billing_interval", "is_featured"]
    search_fields = ["name", "headline", "description", "box_size"]
    ordering_fields = ["sort_order", "price", "cadence_days", "shipment_offset_days"]
    ordering = ["sort_order", "name"]

    def get_queryset(self):
        return SubscriptionPlan.objects.filter(is_active=True).order_by("sort_order", "name")


class SubscriptionPlanDetailAPIView(generics.RetrieveAPIView):
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"

    def get_queryset(self):
        return SubscriptionPlan.objects.filter(is_active=True)


class MySubscriptionListAPIView(generics.ListAPIView):
    serializer_class = UserSubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = DefaultPageNumberPagination
    filterset_fields = ["status", "plan__billing_interval"]
    search_fields = ["plan__name", "plan__headline"]
    ordering_fields = ["created_at", "next_renewal_date", "next_shipment_date"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return UserSubscription.objects.filter(user=self.request.user).select_related("plan").order_by("-created_at")


class MyOrderListAPIView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = DefaultPageNumberPagination
    filterset_fields = ["status", "payment_status", "currency"]
    search_fields = ["order_number", "customer_email"]
    ordering_fields = ["created_at", "placed_at", "total"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by("-created_at")
