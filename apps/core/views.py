from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import DetailView, FormView, TemplateView

from django_ratelimit.decorators import ratelimit

from apps.blog.models import BlogPost
from apps.catalog.models import Product
from apps.core.delivery import get_delhi_ncr_delivery_experience
from apps.core.forms import FAQAssistantForm, NewsletterSignupForm
from apps.core.models import ContactSettings, FAQ, HomepageContent, PolicyPage, SiteSettings, Testimonial
from apps.core.services import answer_support_question
from apps.subscriptions.models import SubscriptionPlan


class CoreContextMixin:
    def get_site_settings(self):
        return SiteSettings.load()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("site_settings", self.get_site_settings())
        context.setdefault("newsletter_form", NewsletterSignupForm())
        context.setdefault("footer_policies", PolicyPage.objects.filter(is_published=True)[:4])
        context.setdefault("delivery_experience", get_delhi_ncr_delivery_experience())
        return context


class HomeView(CoreContextMixin, TemplateView):
    template_name = "pages/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["homepage"] = HomepageContent.load()
        context["featured_testimonials"] = Testimonial.objects.filter(is_featured=True)[:3]
        featured_products = Product.objects.filter(is_active=True, is_featured=True).prefetch_related(
            "images", "variants", "dietary_attributes"
        )[:4]
        seasonal_products = Product.objects.filter(is_active=True, is_seasonal=True).prefetch_related(
            "images", "variants"
        )[:3]
        context["featured_products"] = featured_products
        context["seasonal_products"] = seasonal_products

        hero_rotator_products = [product for product in featured_products if product.primary_image][:3]
        if len(hero_rotator_products) < 3:
            featured_ids = {product.id for product in hero_rotator_products}
            for product in seasonal_products:
                if product.primary_image and product.id not in featured_ids:
                    hero_rotator_products.append(product)
                    featured_ids.add(product.id)
                if len(hero_rotator_products) == 3:
                    break
        context["hero_rotator_products"] = hero_rotator_products

        context["featured_plan"] = SubscriptionPlan.objects.filter(is_active=True, is_featured=True).first()
        context["latest_posts"] = BlogPost.objects.filter(is_published=True).select_related("category")[:3]
        return context


class AboutView(CoreContextMixin, TemplateView):
    template_name = "pages/about.html"


class FAQView(CoreContextMixin, TemplateView):
    template_name = "pages/faq.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        faqs = FAQ.objects.filter(is_published=True)
        grouped_faqs: dict[str, list[FAQ]] = {}
        for faq in faqs:
            grouped_faqs.setdefault(faq.category, []).append(faq)
        context["faqs"] = faqs
        context["grouped_faqs"] = grouped_faqs.items()
        context["faq_assistant_form"] = FAQAssistantForm()
        context["faq_assistant_ai_enabled"] = settings.AI_CHAT_ENABLED and bool(settings.AI_CHAT_API_KEY)
        context["faq_assistant_model_name"] = settings.AI_CHAT_MODEL
        return context


class ContactView(CoreContextMixin, TemplateView):
    template_name = "pages/contact.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["contact_settings"] = ContactSettings.load()
        return context


class PolicyView(CoreContextMixin, DetailView):
    template_name = "pages/policy.html"
    context_object_name = "policy_page"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return PolicyPage.objects.filter(is_published=True)


class NewsletterSignupView(FormView):
    form_class = NewsletterSignupForm
    http_method_names = ["post"]

    # Block IP abuse: 5 signups/hour is generous for a single person using
    # multiple devices but blocks a bot trying to spam the newsletter list.
    @method_decorator(ratelimit(key="ip", rate="5/h", method="POST", block=False))
    def post(self, request, *args, **kwargs):
        if getattr(request, "limited", False):
            messages.info(
                request,
                "You've just subscribed — check your inbox. Try again in a bit if this was a mistake.",
            )
            return redirect(self.get_success_url())
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "You’re on the list for new drops, gifting moments, and seasonal boxes.")
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        for errors in form.errors.values():
            for error in errors:
                messages.error(self.request, error)
        return redirect(self.get_success_url())

    def get_success_url(self):
        return self.request.POST.get("next") or reverse("home")


class FAQAssistantView(View):
    http_method_names = ["get"]

    # FAQAssistantView hits an external AI API (Gemini/OpenAI) on every call
    # so it's the most expensive public endpoint. Two-tier limit:
    #   * burst protection   — 10/min per IP stops mashed-keyboard abuse
    #   * sustained quota    — 60/hour per IP protects the monthly AI budget
    # block=False so we return a friendly JSON error instead of a bare 429.
    @method_decorator(ratelimit(key="ip", rate="10/m", method="GET", block=False))
    @method_decorator(ratelimit(key="ip", rate="60/h", method="GET", block=False))
    def get(self, request, *args, **kwargs):
        if getattr(request, "limited", False):
            return JsonResponse(
                {
                    "ok": False,
                    "answer": (
                        "You've sent a lot of questions in a short time. "
                        "Please wait a minute and try again — or browse the FAQ below."
                    ),
                    "follow_up_questions": list(
                        FAQ.objects.filter(is_published=True).values_list("question", flat=True)[:4]
                    ),
                },
                status=429,
            )

        form = FAQAssistantForm(request.GET)
        if not form.is_valid():
            return JsonResponse(
                {
                    "ok": False,
                    "answer": "Please enter a fuller question so I can help.",
                    "errors": form.errors.get("question", []),
                    "follow_up_questions": list(
                        FAQ.objects.filter(is_published=True).values_list("question", flat=True)[:4]
                    ),
                },
                status=400,
            )

        support_answer = answer_support_question(form.cleaned_data["question"])
        return JsonResponse(
            {
                "ok": True,
                "answer": support_answer.answer,
                "source_title": support_answer.source_title,
                "source_type": support_answer.source_type,
                "follow_up_questions": support_answer.follow_up_questions,
                "cta_label": support_answer.cta_label,
                "cta_url": support_answer.cta_url,
                "confidence": support_answer.confidence,
                "used_ai": support_answer.used_ai,
                "model_name": support_answer.model_name,
            }
        )

