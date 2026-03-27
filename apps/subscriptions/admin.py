from django.contrib import admin

from apps.subscriptions.models import SubscriptionPlan, SubscriptionShipment, UserSubscription


class SubscriptionShipmentInline(admin.TabularInline):
    model = SubscriptionShipment
    extra = 0
    fields = ("scheduled_for", "status", "tracking_reference", "order")
    show_change_link = True


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "billing_interval",
        "cadence_days",
        "shipment_offset_days",
        "box_size",
        "price",
        "is_featured",
        "is_active",
        "sort_order",
    )
    list_filter = ("billing_interval", "is_featured", "is_active", "cadence_days", "shipment_offset_days")
    search_fields = ("name", "headline", "description", "stripe_price_id")
    prepopulated_fields = {"slug": ("name",)}
    list_editable = (
        "cadence_days",
        "shipment_offset_days",
        "price",
        "is_featured",
        "is_active",
        "sort_order",
    )
    fieldsets = (
        (
            "Plan identity",
            {
                "fields": (
                    "name",
                    "slug",
                    "headline",
                    "description",
                )
            },
        ),
        (
            "Cadence & fulfillment",
            {
                "fields": (
                    "billing_interval",
                    "cadence_days",
                    "shipment_offset_days",
                    "box_size",
                )
            },
        ),
        (
            "Pricing & provider",
            {
                "fields": (
                    "price",
                    "compare_at_price",
                    "stripe_price_id",
                )
            },
        ),
        (
            "Merchandising",
            {
                "fields": (
                    "is_featured",
                    "is_active",
                    "sort_order",
                )
            },
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "plan",
        "status",
        "renewal_day",
        "next_renewal_date",
        "next_shipment_date",
        "created_at",
    )
    list_filter = ("status", "plan", "renewal_day")
    search_fields = ("user__email", "stripe_subscription_id", "stripe_customer_id")
    readonly_fields = ("created_at", "updated_at")
    inlines = [SubscriptionShipmentInline]
    fieldsets = (
        (
            "Subscription identity",
            {
                "fields": (
                    "user",
                    "plan",
                    "status",
                    "latest_order",
                )
            },
        ),
        (
            "Recurring schedule",
            {
                "fields": (
                    "renewal_day",
                    "next_renewal_date",
                    "next_shipment_date",
                    "paused_from",
                    "cancelled_at",
                )
            },
        ),
        (
            "Preferences & provider",
            {
                "fields": (
                    "flavor_preferences",
                    "stripe_subscription_id",
                    "stripe_customer_id",
                    "admin_notes",
                )
            },
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )


@admin.register(SubscriptionShipment)
class SubscriptionShipmentAdmin(admin.ModelAdmin):
    list_display = (
        "subscription",
        "scheduled_for",
        "status",
        "tracking_reference",
        "order",
    )
    list_filter = ("status", "scheduled_for")
    search_fields = ("subscription__user__email", "tracking_reference", "order__order_number")
    readonly_fields = ("created_at", "updated_at")
