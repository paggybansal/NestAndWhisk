from django.db import transaction

from apps.cart.models import Cart, CartItem, Wishlist, WishlistItem
from apps.catalog.models import Product, ProductVariant


def get_or_create_cart(*, user=None, session_key=""):
    if user and user.is_authenticated:
        cart, _created = Cart.objects.get_or_create(user=user, is_active=True, defaults={"session_key": session_key})
        return cart
    cart, _created = Cart.objects.get_or_create(session_key=session_key, is_active=True, defaults={"user": None})
    return cart


def deactivate_cart(*, cart: Cart):
    if not cart.is_active:
        return cart
    cart.is_active = False
    cart.save(update_fields=["is_active", "updated_at"])
    return cart


@transaction.atomic
def add_product_to_cart(*, cart: Cart, product: Product, variant: ProductVariant | None, quantity: int):
    unit_price = variant.price if variant else product.price_from
    item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        variant=variant,
        defaults={
            "quantity": quantity,
            "unit_price": unit_price,
        },
    )
    if not created:
        item.quantity += quantity
        item.unit_price = unit_price
        item.save(update_fields=["quantity", "unit_price", "updated_at"])
    return item


@transaction.atomic
def update_cart_item_quantity(*, item: CartItem, quantity: int):
    if quantity <= 0:
        item.delete()
        return None
    item.quantity = quantity
    item.save(update_fields=["quantity", "updated_at"])
    return item


@transaction.atomic
def increment_cart_item_quantity(*, item: CartItem, delta: int):
    return update_cart_item_quantity(item=item, quantity=item.quantity + delta)


def get_or_create_wishlist(user):
    wishlist, _created = Wishlist.objects.get_or_create(user=user)
    return wishlist


def toggle_wishlist_product(*, wishlist: Wishlist, product: Product):
    item = WishlistItem.objects.filter(wishlist=wishlist, product=product).first()
    if item:
        item.delete()
        return False
    WishlistItem.objects.create(wishlist=wishlist, product=product)
    return True
