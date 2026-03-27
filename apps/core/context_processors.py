from django.conf import settings as django_settings

from apps.core.branding import get_brand_logo_path
from apps.core.forms import NewsletterSignupForm
from apps.core.models import FAQ, PolicyPage, SiteSettings


def shared_site_context(_request):
    return {
        "site_settings": SiteSettings.load(),
        "brand_logo_url": get_brand_logo_path(),
        "store_currency_code": django_settings.STRIPE_CURRENCY.upper(),
        "store_currency_symbol": "₹",
        "newsletter_form": NewsletterSignupForm(),
        "footer_policies": PolicyPage.objects.filter(is_published=True)[:4],
        "faq_chatbot_starters": list(
            FAQ.objects.filter(is_published=True).values_list("question", flat=True)[:4]
        ),
    }

