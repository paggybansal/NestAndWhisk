from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap as sitemap_view
from django.http import HttpResponse, HttpResponsePermanentRedirect
from django.urls import include, path, re_path
from django.views.decorators.cache import cache_control
from django.views.static import serve as static_serve

from apps.core.sitemaps import SITEMAPS


def healthcheck(_request):
    return HttpResponse("ok", content_type="text/plain")


@cache_control(max_age=60 * 60 * 6, public=True)
def robots_txt(request):
    """Plain-text crawler directives. Points bots at the sitemap."""
    host = request.get_host()
    scheme = "https" if request.is_secure() else request.scheme
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /account/",
        "Disallow: /cart/",
        "Disallow: /checkout/",
        "Disallow: /api/",
        "Allow: /",
        "",
        f"Sitemap: {scheme}://{host}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain")


def legacy_accounts_redirect(request, subpath: str = ""):
    target_suffix = subpath or "login/"
    target = f"/account/{target_suffix}"
    query_string = request.META.get("QUERY_STRING")
    if query_string:
        target = f"{target}?{query_string}"
    return HttpResponsePermanentRedirect(target)


urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("", include("apps.core.urls")),
    path("journal/", include("apps.blog.urls")),
    path("shop/", include("apps.catalog.urls")),
    path("cart/", include("apps.cart.urls")),
    path("checkout/", include("apps.checkout.urls")),
    path("reviews/", include("apps.reviews.urls")),
    path("account/", include("apps.accounts.urls")),
    path("account/", include("apps.accounts.allauth_urls")),
    path("corporate/", include("apps.corporate.urls")),
    path("subscriptions/", include("apps.subscriptions.urls")),
    path("api/", include("apps.api.urls")),
    path("accounts/", legacy_accounts_redirect, name="legacy_accounts_root"),
    path("accounts/<path:subpath>", legacy_accounts_redirect, name="legacy_accounts_redirect"),
    path("health/", healthcheck, name="healthcheck"),
    path(
        "sitemap.xml",
        cache_control(max_age=60 * 60, public=True)(sitemap_view),
        {"sitemaps": SITEMAPS},
        name="sitemap",
    ),
    path("robots.txt", robots_txt, name="robots_txt"),
]

if getattr(settings, "SERVE_MEDIA_FILES", False):
    media_prefix = settings.MEDIA_URL.lstrip("/")
    urlpatterns += [
        re_path(
            rf"^{media_prefix}(?P<path>.*)$",
            static_serve,
            {"document_root": settings.MEDIA_ROOT},
        )
    ]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
