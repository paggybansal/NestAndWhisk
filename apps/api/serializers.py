from rest_framework import serializers

from apps.orders.models import Order
from apps.subscriptions.models import SubscriptionPlan, UserSubscription


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    billing_interval_display = serializers.CharField(source="get_billing_interval_display", read_only=True)

    class Meta:
        model = SubscriptionPlan
        fields = [
            "id",
            "name",
            "slug",
            "headline",
            "description",
            "billing_interval",
            "billing_interval_display",
            "cadence_days",
            "shipment_offset_days",
            "box_size",
            "price",
            "compare_at_price",
            "is_featured",
        ]


class UserSubscriptionSerializer(serializers.ModelSerializer):
    plan = SubscriptionPlanSerializer(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = UserSubscription
        fields = [
            "id",
            "plan",
            "status",
            "status_display",
            "flavor_preferences",
            "renewal_day",
            "next_renewal_date",
            "next_shipment_date",
            "paused_from",
            "cancelled_at",
            "created_at",
        ]


class OrderSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    payment_status_display = serializers.CharField(source="get_payment_status_display", read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "status",
            "status_display",
            "payment_status",
            "payment_status_display",
            "total",
            "currency",
            "preferred_delivery_date",
            "placed_at",
            "created_at",
        ]
