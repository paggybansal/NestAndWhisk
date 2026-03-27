from django.urls import path

from apps.reviews.views import ProductReviewCreateView

app_name = "reviews"

urlpatterns = [
    path("products/<slug:slug>/submit/", ProductReviewCreateView.as_view(), name="product_review_create"),
]

