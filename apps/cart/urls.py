from django.urls import path

from apps.cart.views import (
    AddToCartView,
    BuildABoxView,
    CartDetailView,
    CartItemStepQuantityView,
    CartItemUpdateView,
    RemoveCartItemView,
    WishlistDetailView,
    WishlistToggleView,
)

app_name = "cart"

urlpatterns = [
    path("", CartDetailView.as_view(), name="detail"),
    path("build-a-box/", BuildABoxView.as_view(), name="build_a_box"),
    path("add/<slug:slug>/", AddToCartView.as_view(), name="add"),
    path("update/<int:pk>/", CartItemUpdateView.as_view(), name="update"),
    path("update-step/<int:pk>/", CartItemStepQuantityView.as_view(), name="update_step"),
    path("remove/<int:pk>/", RemoveCartItemView.as_view(), name="remove"),
    path("wishlist/", WishlistDetailView.as_view(), name="wishlist"),
    path("wishlist/toggle/<slug:slug>/", WishlistToggleView.as_view(), name="wishlist_toggle"),
]
