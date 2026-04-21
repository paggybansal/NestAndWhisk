from django.db.models import Count, Min, Prefetch, Q
from django.views.generic import DetailView, ListView

from apps.cart.models import WishlistItem
from apps.catalog.forms import CatalogFilterForm
from apps.catalog.models import Product, ProductCategory, ProductVariant
from apps.core.views import CoreContextMixin
from apps.reviews.forms import ReviewForm
from apps.reviews.models import Review


class ShopView(CoreContextMixin, ListView):
    template_name = "catalog/shop.html"
    model = Product
    context_object_name = "products"
    paginate_by = 12

    def get_filter_form(self):
        return CatalogFilterForm(self.request.GET or None)

    def get_queryset(self):
        queryset = (
            Product.objects.filter(is_active=True)
            .select_related("category")
            .prefetch_related("dietary_attributes", "tags", "images", "variants")
            .annotate(min_price=Min("variants__price"))
        )
        ordering_map = {
            "featured": ["-is_featured", "sort_order", "name", "id"],
            "newest": ["-created_at", "name", "id"],
            "price_asc": ["min_price", "name", "id"],
            "price_desc": ["-min_price", "name", "id"],
            "name": ["name", "id"],
        }
        sort = "featured"
        form = self.get_filter_form()
        if form.is_valid():
            search = form.cleaned_data.get("search")
            category = form.cleaned_data.get("category")
            dietary = form.cleaned_data.get("dietary")
            in_stock = form.cleaned_data.get("in_stock")
            sort = form.cleaned_data.get("sort") or "featured"

            if search:
                queryset = queryset.filter(
                    Q(name__icontains=search)
                    | Q(short_description__icontains=search)
                    | Q(description__icontains=search)
                )
            if category:
                queryset = queryset.filter(category=category)
            if dietary:
                queryset = queryset.filter(dietary_attributes=dietary)
            if in_stock:
                queryset = queryset.filter(variants__inventory_quantity__gt=0, variants__is_active=True)

        # Always apply a deterministic ordering — pagination across an
        # unordered queryset can repeat/skip rows (and Django warns about it).
        # The trailing `id` is a tiebreaker to keep pagination stable when the
        # primary key tie happens (e.g. identical min_price across products).
        return queryset.order_by(*ordering_map.get(sort, ordering_map["featured"])).distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = self.get_filter_form()
        request_query = self.request.GET.copy()
        request_query.pop("page", None)
        category_base_query = request_query.copy()
        category_base_query.pop("category", None)

        active_filter_count = 0
        current_search = ""
        current_category_slug = ""
        current_sort = "featured"
        if form.is_valid():
            current_search = form.cleaned_data.get("search") or ""
            current_category = form.cleaned_data.get("category")
            current_dietary = form.cleaned_data.get("dietary")
            current_in_stock = form.cleaned_data.get("in_stock")
            current_sort = form.cleaned_data.get("sort") or "featured"
            current_category_slug = current_category.slug if current_category else ""
            active_filter_count = sum(
                bool(value)
                for value in [current_search, current_category, current_dietary, current_in_stock]
            )
            if current_sort != "featured":
                active_filter_count += 1
        else:
            current_category_slug = self.request.GET.get("category", "")
            current_sort = self.request.GET.get("sort", "featured") or "featured"
            current_search = self.request.GET.get("search", "")

        context["filter_form"] = form
        context["categories"] = ProductCategory.objects.filter(is_active=True).annotate(
            active_product_count=Count("products", filter=Q(products__is_active=True), distinct=True)
        )
        context["active_filter_count"] = active_filter_count
        context["current_search"] = current_search
        context["current_category_slug"] = current_category_slug
        context["current_sort"] = current_sort
        context["current_querystring"] = request_query.urlencode()
        context["category_base_querystring"] = category_base_query.urlencode()
        return context


class ProductDetailView(CoreContextMixin, DetailView):
    template_name = "catalog/product_detail.html"
    model = Product
    context_object_name = "product"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return (
            Product.objects.filter(is_active=True)
            .select_related("category")
            .prefetch_related(
                "dietary_attributes",
                "tags",
                "images",
                Prefetch(
                    "variants",
                    queryset=ProductVariant.objects.filter(is_active=True).order_by("sort_order", "price"),
                ),
                Prefetch(
                    "reviews",
                    queryset=Review.objects.filter(is_approved=True).order_by("-created_at"),
                ),
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["related_products"] = (
            Product.objects.filter(category=self.object.category, is_active=True)
            .exclude(pk=self.object.pk)
            .prefetch_related("images", "variants")[:4]
        )
        context["ingredient_highlights"] = self.object.ingredient_highlight_items
        context["texture_meter"] = self.object.texture_meter_items
        context["pairings"] = self.object.pairing_items
        context["shelf_life_summary"] = self.object.shelf_life_display
        context["storage_guidance"] = self.object.storage_guidance_display
        context["serving_tip"] = self.object.serving_tip_display
        context["has_product_video"] = self.object.has_product_video
        context["product_video_kind"] = self.object.product_video_kind
        context["product_video_embed_url"] = self.object.product_video_embed_url
        context["product_video_caption"] = self.object.product_video_caption_display
        context["product_video_poster_url"] = self.object.product_video_poster_url
        initial = {}
        if self.request.user.is_authenticated:
            initial = {
                "customer_name": self.request.user.full_name,
                "customer_email": self.request.user.email,
            }
            context["wishlist_product_ids"] = set(
                WishlistItem.objects.filter(wishlist__user=self.request.user).values_list("product_id", flat=True)
            )
        else:
            context["wishlist_product_ids"] = set()
        context["review_form"] = ReviewForm(initial=initial)
        context["approved_reviews"] = self.object.reviews.all()
        return context
