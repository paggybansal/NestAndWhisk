from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import FormView, TemplateView, View

from apps.cart.forms import BUILD_A_BOX_CATEGORY_SLUG, AddToCartForm, BuildABoxForm, CartItemUpdateForm
from apps.cart.models import CartItem
from apps.cart.services import (
    add_build_a_box_to_cart,
    add_product_to_cart,
    get_or_create_cart,
    get_or_create_wishlist,
    increment_cart_item_quantity,
    toggle_wishlist_product,
    update_cart_item_quantity,
)
from apps.catalog.models import Product, ProductVariant
from apps.core.delivery import get_delhi_ncr_delivery_experience
from apps.core.views import CoreContextMixin


class CartDetailView(CoreContextMixin, TemplateView):
    template_name = "cart/detail.html"

    def get_cart(self):
        session_key = self.request.session.session_key
        if not session_key:
            self.request.session.create()
            session_key = self.request.session.session_key
        return get_or_create_cart(user=self.request.user, session_key=session_key or "")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cart"] = self.get_cart()
        return context


class AddToCartView(View):
    http_method_names = ["post"]

    def post(self, request, slug):
        product = get_object_or_404(Product, slug=slug, is_active=True)
        form = AddToCartForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Please review the cart options and try again.")
            return redirect(product.get_absolute_url())

        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key

        cart = get_or_create_cart(user=request.user, session_key=session_key or "")
        variant = None
        variant_id = form.cleaned_data.get("variant_id")
        if variant_id:
            variant = get_object_or_404(ProductVariant, pk=variant_id, product=product, is_active=True)

        add_product_to_cart(
            cart=cart,
            product=product,
            variant=variant,
            quantity=form.cleaned_data["quantity"],
            gift_message=form.cleaned_data.get("gift_message", ""),
            packaging_option=form.cleaned_data.get("packaging_option", ""),
        )
        messages.success(request, f"{product.name} was added to your cart.")
        return redirect("cart:detail")


class CartHtmxMixin:
    def render_cart_content(self, request, cart):
        return render(
            request,
            "cart/_cart_content.html",
            {
                "cart": cart,
                "delivery_experience": get_delhi_ncr_delivery_experience(),
            },
        )


class CartItemUpdateView(CartHtmxMixin, View):
    http_method_names = ["post"]

    def post(self, request: HttpRequest, pk: int):
        item = get_object_or_404(CartItem, pk=pk)
        form = CartItemUpdateForm(request.POST)
        if form.is_valid():
            updated_item = update_cart_item_quantity(item=item, quantity=form.cleaned_data["quantity"])
            if request.headers.get("HX-Request"):
                cart = item.cart if updated_item else get_or_create_cart(user=request.user, session_key=item.cart.session_key)
                return self.render_cart_content(request, cart)
            messages.success(request, "Cart updated.")
        else:
            messages.error(request, "Please enter a valid quantity.")
        return redirect("cart:detail")


class CartItemStepQuantityView(CartHtmxMixin, View):
    http_method_names = ["post"]

    def post(self, request: HttpRequest, pk: int):
        item = get_object_or_404(CartItem, pk=pk)
        delta = int(request.POST.get("delta", 0))
        updated_item = increment_cart_item_quantity(item=item, delta=delta)
        cart = item.cart if updated_item else get_or_create_cart(user=request.user, session_key=item.cart.session_key)
        if request.headers.get("HX-Request"):
            return self.render_cart_content(request, cart)
        messages.success(request, "Cart updated.")
        return redirect("cart:detail")


class RemoveCartItemView(CartHtmxMixin, View):
    http_method_names = ["post"]

    def post(self, request, pk):
        item = get_object_or_404(CartItem, pk=pk)
        cart = item.cart
        item.delete()
        if request.headers.get("HX-Request"):
            return self.render_cart_content(request, cart)
        messages.success(request, "Item removed from your cart.")
        return redirect("cart:detail")


class BuildABoxView(CoreContextMixin, FormView):
    template_name = "cart/build_a_box.html"
    form_class = BuildABoxForm

    def get_initial(self):
        initial = super().get_initial()
        base_product = (
            Product.objects.filter(
                is_active=True,
                allows_build_a_box=True,
                category__slug=BUILD_A_BOX_CATEGORY_SLUG,
            )
            .order_by("sort_order", "name")
            .first()
        )
        if base_product:
            initial["base_product"] = base_product.pk
            initial_variant = base_product.variants.filter(is_active=True, inventory_quantity__gt=0).order_by("sort_order", "price").first()
            if initial_variant:
                initial["variant"] = initial_variant.pk
        return initial

    def form_valid(self, form):
        session_key = self.request.session.session_key
        if not session_key:
            self.request.session.create()
            session_key = self.request.session.session_key
        cart = get_or_create_cart(user=self.request.user, session_key=session_key or "")
        add_build_a_box_to_cart(
            cart=cart,
            product=form.cleaned_data["base_product"],
            variant=form.cleaned_data["variant"],
            quantity=form.cleaned_data["quantity"],
            flavors=form.cleaned_data["flavors"],
            gift_message=form.cleaned_data.get("gift_message", ""),
            packaging_option=form.cleaned_data.get("packaging_option", ""),
        )
        messages.success(self.request, "Your custom cookie box was added to the cart.")
        return redirect("cart:detail")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["buildable_products"] = (
            Product.objects.filter(is_active=True, allows_build_a_box=True)
            .exclude(category__slug=BUILD_A_BOX_CATEGORY_SLUG)
            .prefetch_related("variants")
        )
        return context


class WishlistDetailView(LoginRequiredMixin, CoreContextMixin, TemplateView):
    template_name = "cart/wishlist.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["wishlist"] = get_or_create_wishlist(self.request.user)
        return context


class WishlistToggleView(LoginRequiredMixin, View):
    http_method_names = ["post"]

    def post(self, request, slug):
        product = get_object_or_404(Product, slug=slug, is_active=True)
        wishlist = get_or_create_wishlist(request.user)
        added = toggle_wishlist_product(wishlist=wishlist, product=product)
        messages.success(
            request,
            f"{product.name} {'added to' if added else 'removed from'} your wishlist.",
        )
        return redirect(request.POST.get("next") or product.get_absolute_url())
