from django.contrib import admin

from apps.reviews.models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "customer_name",
        "rating",
        "is_approved",
        "is_verified_purchase",
        "created_at",
    )
    list_filter = ("rating", "is_approved", "is_verified_purchase", "product__category")
    search_fields = ("product__name", "customer_name", "customer_email", "title", "body")
    list_editable = ("is_approved", "is_verified_purchase")
