"""
Sitemap definitions exposed at /sitemap.xml.

Each sitemap relies on Django's built-in ``django.contrib.sites``
machinery, so the absolute URLs emitted use the domain stored on the
``Site`` row pointed at by ``SITE_ID``. The entrypoint keeps that row
in sync with the deploy's public host via the ``SITE_DOMAIN`` env var
so the sitemap (and allauth emails) always match the live URL.
"""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from apps.blog.models import BlogPost
from apps.catalog.models import Product
from apps.core.models import PolicyPage


class StaticViewSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8
    protocol = "https"

    def items(self):
        # Hand-picked public, indexable top-level pages. Anything with a
        # login requirement, dynamic state, or transactional intent is
        # intentionally excluded (cart, checkout, account, admin).
        return [
            "home",
            "about",
            "faq",
            "contact",
            "catalog:shop",
            "blog:list",
            "subscriptions:list",
            "corporate:inquiry",
        ]

    def location(self, item: str) -> str:  # type: ignore[override]
        try:
            return reverse(item)
        except Exception:  # noqa: BLE001
            # A renamed or missing URL must never 500 the sitemap.
            return "/"


class ProductSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.9
    protocol = "https"

    def items(self):
        return Product.objects.filter(is_active=True).only("slug", "updated_at")

    def lastmod(self, obj: Product):
        return obj.updated_at


class BlogPostSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.6
    protocol = "https"

    def items(self):
        return BlogPost.objects.filter(is_published=True).only(
            "slug", "updated_at", "published_at"
        )

    def lastmod(self, obj: BlogPost):
        return obj.updated_at or obj.published_at


class PolicyPageSitemap(Sitemap):
    changefreq = "yearly"
    priority = 0.3
    protocol = "https"

    def items(self):
        return PolicyPage.objects.filter(is_published=True).only("slug", "updated_at")

    def location(self, obj: PolicyPage) -> str:  # type: ignore[override]
        return reverse("policy", kwargs={"slug": obj.slug})

    def lastmod(self, obj: PolicyPage):
        return obj.updated_at


SITEMAPS = {
    "static": StaticViewSitemap,
    "products": ProductSitemap,
    "posts": BlogPostSitemap,
    "policies": PolicyPageSitemap,
}
