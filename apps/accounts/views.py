from allauth.account.views import LoginView, PasswordResetView, SignupView
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse, reverse_lazy
from django.views.generic import TemplateView, UpdateView

from apps.accounts.forms import (
    CustomerLoginForm,
    CustomerProfileForm,
    CustomerResetPasswordForm,
    CustomerSignupForm,
)
from apps.accounts.models import User
from apps.orders.models import Order


class AccountAuthContextMixin:
    extra_context = {
        "auth_eyebrow": "Nest & Whisk account",
    }


class CustomerLoginView(AccountAuthContextMixin, LoginView):
    form_class = CustomerLoginForm
    template_name = "account/login.html"
    extra_context = {
        "auth_eyebrow": "Nest & Whisk account",
        "auth_title": "Welcome back to the bakery.",
        "auth_body": "Sign in to manage orders, subscriptions, gifting details, and saved preferences—all in one warm, polished account experience.",
    }


class CustomerSignupView(AccountAuthContextMixin, SignupView):
    form_class = CustomerSignupForm
    template_name = "account/signup.html"
    extra_context = {
        "auth_eyebrow": "Create your account",
        "auth_title": "A more thoughtful way to gift and reorder.",
        "auth_body": "Create your account to save gifting details, track seasonal orders, and stay close to new cookie launches.",
    }


class CustomerPasswordResetView(AccountAuthContextMixin, PasswordResetView):
    form_class = CustomerResetPasswordForm
    template_name = "account/password_reset.html"
    extra_context = {
        "auth_eyebrow": "Password help",
        "auth_title": "Let’s get you back in.",
        "auth_body": "We’ll send a secure reset link to the email address associated with your Nest & Whisk account.",
    }


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dashboard_sections"] = [
            {
                "title": "Orders",
                "body": "Track recent purchases, reorder favorites, and review gifting details.",
                "url": reverse("account_orders"),
                "cta": "View your orders",
                "meta": "Payment and delivery status",
            },
            {
                "title": "Subscriptions",
                "body": "Manage delivery cadence, flavor preferences, and billing status.",
                "url": reverse("subscriptions:dashboard"),
                "cta": "Manage subscriptions",
                "meta": "Pause, resume, or update your rhythm",
            },
            {
                "title": "Saved details",
                "body": "Keep addresses and preferences ready for a seamless checkout.",
                "url": reverse("account_profile"),
                "cta": "Update saved details",
                "meta": "Profile, email, and account tools",
            },
        ]
        return context


class AccountOrdersView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/orders.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        orders = Order.objects.filter(user=self.request.user).prefetch_related("items", "payments")
        context.update(
            {
                "orders": orders,
                "lookup_url": reverse_lazy("checkout:lookup"),
            }
        )
        return context


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = CustomerProfileForm
    template_name = "accounts/profile.html"
    success_url = reverse_lazy("account_profile")

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, "Your account details have been updated.")
        return super().form_valid(form)
