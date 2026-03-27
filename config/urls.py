from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponse, HttpResponsePermanentRedirect
from django.urls import include, path, re_path
from django.views.static import serve as static_serve


def healthcheck(_request):
    return HttpResponse("ok", content_type="text/plain")


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
