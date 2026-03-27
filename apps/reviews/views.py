from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import FormView

from apps.catalog.models import Product
from apps.reviews.forms import ReviewForm


class ProductReviewCreateView(FormView):
    form_class = ReviewForm
    http_method_names = ["post"]

    def dispatch(self, request, *args, **kwargs):
        self.product = get_object_or_404(Product, slug=kwargs["slug"], is_active=True)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        review = form.save(commit=False)
        review.product = self.product
        if self.request.user.is_authenticated:
            review.user = self.request.user
            if not review.customer_name:
                review.customer_name = self.request.user.full_name
            if not review.customer_email:
                review.customer_email = self.request.user.email
        review.save()
        messages.success(
            self.request,
            "Thank you for sharing your experience. Your review is pending approval.",
        )
        return redirect(self.product.get_absolute_url())

    def form_invalid(self, form):
        for errors in form.errors.values():
            for error in errors:
                messages.error(self.request, error)
        return redirect(self.product.get_absolute_url())

