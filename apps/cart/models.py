from decimal import Decimal
from uuid import uuid4

from django.conf import settings
from django.db import models

from apps.catalog.models import Product, ProductVariant
from apps.core.models import TimeStampedModel


class Cart(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="carts",
        null=True,
        blank=True,
    )
    session_key = models.CharField(max_length=64, blank=True, db_index=True)
    token = models.UUIDField(default=uuid4, editable=False, unique=True)
    coupon_code = models.CharField(max_length=50, blank=True)
    gift_note = models.CharField(max_length=255, blank=True)
    is_gift_wrapped = models.BooleanField(default=False)
    preferred_delivery_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["session_key", "is_active"]),
            models.Index(fields=["user", "is_active"]),
        ]

    def __str__(self) -> str:
        owner = self.user.email if self.user else self.session_key or self.token
        return f"Cart {owner}"

    @property
    def subtotal(self) -> Decimal:
        return sum((item.line_total for item in self.items.all()), Decimal("0.00"))

    @property
    def item_count(self) -> int:
        return sum(item.quantity for item in self.items.all())


class CartItem(TimeStampedModel):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="cart_items")
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name="cart_items",
        null=True,
        blank=True,
    )
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    build_a_box_payload = models.JSONField(default=dict, blank=True)
    gift_message = models.CharField(max_length=255, blank=True)
    packaging_option = models.CharField(max_length=80, blank=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["cart", "product", "variant"],
                name="unique_cart_item_per_variant",
            )
        ]

    def __str__(self) -> str:
        return f"{self.quantity} × {self.product.name}"

    @property
    def line_total(self) -> Decimal:
        return self.unit_price * self.quantity


class Wishlist(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wishlist",
    )

    class Meta:
        verbose_name = "wishlist"
        verbose_name_plural = "wishlists"

    def __str__(self) -> str:
        return f"Wishlist for {self.user.email}"


class WishlistItem(TimeStampedModel):
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="wishlist_items")

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["wishlist", "product"],
                name="unique_wishlist_product",
            )
        ]

    def __str__(self) -> str:
        return f"{self.product.name} in wishlist"
