from django.urls import path

from apps.catalog.views import ProductDetailView, ShopView

app_name = "catalog"

urlpatterns = [
    path("", ShopView.as_view(), name="shop"),
    path("<slug:slug>/", ProductDetailView.as_view(), name="product_detail"),
]

