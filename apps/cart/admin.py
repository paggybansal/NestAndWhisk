from django.contrib import admin

from apps.cart.models import Cart, CartItem, Wishlist, WishlistItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    fields = (
        "product",
        "variant",
        "quantity",
        "unit_price",
    )


class WishlistItemInline(admin.TabularInline):
    model = WishlistItem
    extra = 0
    fields = ("product",)


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "session_key", "item_count", "subtotal", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("user__email", "session_key", "coupon_code")
    inlines = [CartItemInline]


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "updated_at")
    search_fields = ("user__email",)
    inlines = [WishlistItemInline]
