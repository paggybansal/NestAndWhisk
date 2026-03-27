from django.contrib import admin
from django.utils import timezone

from apps.orders.models import Order, OrderItem, Payment, PaymentEvent, PaymentWebhookEvent


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = (
        "product_name",
        "variant_name",
        "sku",
        "quantity",
        "unit_price",
        "line_total",
        "gift_message",
        "packaging_option",
    )
    readonly_fields = (
        "product_name",
        "variant_name",
        "sku",
        "quantity",
        "unit_price",
        "line_total",
    )


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    fields = (
        "provider",
        "status",
        "amount",
        "currency",
        "provider_payment_id",
        "provider_checkout_id",
        "provider_reference",
        "receipt_url",
        "paid_at",
    )
    readonly_fields = (
        "provider",
        "amount",
        "currency",
        "provider_payment_id",
        "provider_checkout_id",
        "provider_reference",
        "receipt_url",
        "paid_at",
    )
    show_change_link = True


class PaymentEventInline(admin.TabularInline):
    model = PaymentEvent
    extra = 0
    fields = ("event_type", "provider_reference", "amount", "currency", "occurred_at")
    readonly_fields = ("event_type", "provider_reference", "amount", "currency", "occurred_at")
    show_change_link = True


class PaymentWebhookEventInline(admin.TabularInline):
    model = PaymentWebhookEvent
    extra = 0
    fields = ("event_id", "event_type", "object_id", "is_processed", "processed_at", "processing_notes")
    readonly_fields = ("event_id", "event_type", "object_id", "processed_at", "processing_notes")
    show_change_link = True


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number",
        "customer_email",
        "status",
        "payment_status",
        "total",
        "currency",
        "placed_at",
    )
    list_filter = (
        "status",
        "payment_status",
        "currency",
        "is_gift_wrapped",
        "preferred_delivery_date",
    )
    search_fields = (
        "order_number",
        "customer_email",
        "customer_first_name",
        "customer_last_name",
        "provider_payment_id",
        "provider_checkout_id",
    )
    readonly_fields = (
        "order_number",
        "token",
        "subtotal",
        "discount_total",
        "shipping_total",
        "total",
        "placed_at",
        "created_at",
        "updated_at",
    )
    list_editable = ("status", "payment_status")
    inlines = [OrderItemInline, PaymentInline, PaymentWebhookEventInline]
    fieldsets = (
        (
            "Order identity",
            {
                "fields": (
                    "order_number",
                    "token",
                    "user",
                    "cart",
                    "status",
                    "payment_status",
                    "placed_at",
                )
            },
        ),
        (
            "Customer",
            {
                "fields": (
                    "customer_email",
                    "customer_first_name",
                    "customer_last_name",
                    "customer_phone",
                )
            },
        ),
        (
            "Shipping",
            {
                "fields": (
                    "shipping_address_line_1",
                    "shipping_address_line_2",
                    "shipping_city",
                    "shipping_state",
                    "shipping_postal_code",
                    "shipping_country",
                    "delivery_notes",
                    "preferred_delivery_date",
                )
            },
        ),
        (
            "Gifting",
            {
                "fields": (
                    "gift_note",
                    "is_gift_wrapped",
                )
            },
        ),
        (
            "Payment provider",
            {
                "fields": (
                    "provider",
                    "provider_payment_id",
                    "provider_checkout_id",
                )
            },
        ),
        (
            "Totals",
            {
                "fields": (
                    "currency",
                    "subtotal",
                    "discount_total",
                    "shipping_total",
                    "total",
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


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = (
        "order",
        "product_name",
        "variant_name",
        "quantity",
        "unit_price",
        "line_total",
    )
    search_fields = ("order__order_number", "product_name", "variant_name", "sku")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "order",
        "provider",
        "status",
        "amount",
        "currency",
        "provider_reference",
        "paid_at",
        "created_at",
    )
    list_filter = ("provider", "status", "currency")
    search_fields = (
        "order__order_number",
        "provider_payment_id",
        "provider_checkout_id",
        "provider_reference",
    )
    readonly_fields = ("created_at", "updated_at", "raw_response")
    inlines = [PaymentEventInline, PaymentWebhookEventInline]
    fieldsets = (
        (
            "Payment overview",
            {
                "fields": (
                    "order",
                    "provider",
                    "status",
                    "amount",
                    "currency",
                    "paid_at",
                )
            },
        ),
        (
            "Provider references",
            {
                "fields": (
                    "provider_payment_id",
                    "provider_checkout_id",
                    "provider_reference",
                    "receipt_url",
                )
            },
        ),
        (
            "Webhook payload",
            {
                "fields": ("raw_response", "created_at", "updated_at")
            },
        ),
    )


@admin.action(description="Mark selected webhook events as unprocessed")
def mark_webhook_events_unprocessed(modeladmin, request, queryset):
    queryset.update(is_processed=False, processed_at=None, processing_notes="reset by admin")


@admin.action(description="Mark selected webhook events as processed now")
def mark_webhook_events_processed(modeladmin, request, queryset):
    queryset.update(is_processed=True, processed_at=timezone.now(), processing_notes="manually marked processed")


@admin.register(PaymentWebhookEvent)
class PaymentWebhookEventAdmin(admin.ModelAdmin):
    list_display = (
        "event_id",
        "provider",
        "event_type",
        "object_id",
        "payment",
        "order",
        "is_processed",
        "processed_at",
    )
    list_filter = ("provider", "event_type", "is_processed")
    search_fields = ("event_id", "object_id", "payment__provider_payment_id", "order__order_number")
    readonly_fields = ("created_at", "updated_at", "payload")
    actions = [mark_webhook_events_unprocessed, mark_webhook_events_processed]
    fieldsets = (
        (
            "Webhook delivery",
            {
                "fields": (
                    "provider",
                    "event_id",
                    "event_type",
                    "object_id",
                    "payment",
                    "order",
                )
            },
        ),
        (
            "Processing state",
            {
                "fields": (
                    "is_processed",
                    "processed_at",
                    "processing_notes",
                )
            },
        ),
        (
            "Payload",
            {
                "fields": ("payload", "created_at", "updated_at")
            },
        ),
    )


@admin.register(PaymentEvent)
class PaymentEventAdmin(admin.ModelAdmin):
    list_display = (
        "payment",
        "event_type",
        "provider_reference",
        "amount",
        "currency",
        "occurred_at",
    )
    list_filter = ("event_type", "currency")
    search_fields = ("payment__provider_payment_id", "payment__order__order_number", "provider_reference")
    readonly_fields = ("created_at", "updated_at", "payload")
    fieldsets = (
        (
            "Event details",
            {
                "fields": (
                    "payment",
                    "event_type",
                    "provider_reference",
                    "amount",
                    "currency",
                    "occurred_at",
                )
            },
        ),
        (
            "Payload",
            {
                "fields": ("payload", "created_at", "updated_at")
            },
        ),
    )
