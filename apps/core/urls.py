from django.urls import path

from apps.core.views import (
    AboutView,
    ContactView,
    FAQAssistantView,
    FAQView,
    HomeView,
    NewsletterSignupView,
    PolicyView,
)

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("our-story/", AboutView.as_view(), name="about"),
    path("faq/", FAQView.as_view(), name="faq"),
    path("faq/assistant/", FAQAssistantView.as_view(), name="faq_assistant"),
    path("contact/", ContactView.as_view(), name="contact"),
    path("policies/<slug:slug>/", PolicyView.as_view(), name="policy"),
    path("newsletter-signup/", NewsletterSignupView.as_view(), name="newsletter_signup"),
]
