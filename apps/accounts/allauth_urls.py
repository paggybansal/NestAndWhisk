from allauth.account import urls as account_urls
from allauth.socialaccount import urls as socialaccount_urls

EXCLUDED_ACCOUNT_ROUTE_NAMES = {
    "account_login",
    "account_signup",
    "account_reset_password",
}

urlpatterns = [
    pattern
    for pattern in account_urls.urlpatterns
    if getattr(pattern, "name", None) not in EXCLUDED_ACCOUNT_ROUTE_NAMES
]
urlpatterns += socialaccount_urls.urlpatterns

