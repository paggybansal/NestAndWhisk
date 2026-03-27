from datetime import date

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import DetailView, FormView, TemplateView, View

from apps.core.views import CoreContextMixin
from apps.subscriptions.forms import (
    SubscriptionPreferencesForm,
    SubscriptionSignupForm,
)
from apps.subscriptions.models import SubscriptionPlan, UserSubscription


class SubscriptionPlanListView(CoreContextMixin, TemplateView):
    template_name = "subscriptions/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        plans = SubscriptionPlan.objects.filter(is_active=True).order_by("sort_order", "name")
        context["plans"] = plans
        context["featured_plan"] = plans.filter(is_featured=True).first()
        return context


class SubscriptionPlanDetailView(CoreContextMixin, DetailView):
    template_name = "subscriptions/detail.html"
    context_object_name = "plan"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return SubscriptionPlan.objects.filter(is_active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["related_plans"] = SubscriptionPlan.objects.filter(is_active=True).exclude(pk=self.object.pk)[:3]
        context["signup_form"] = SubscriptionSignupForm(initial={"plan": self.object, "renewal_day": 1})
        context["dashboard_url"] = reverse("subscriptions:dashboard")
        context["signup_url"] = reverse("subscriptions:signup")
        context["guest_cta_url"] = f"{reverse('account_login')}?next={reverse('subscriptions:detail', kwargs={'slug': self.object.slug})}"
        return context


class SubscriptionSignupView(LoginRequiredMixin, CoreContextMixin, FormView):
    form_class = SubscriptionSignupForm
    http_method_names = ["post"]

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if "plan" in self.request.POST:
            kwargs.setdefault("initial", {})["plan"] = self.request.POST.get("plan")
        return kwargs

    def _build_dashboard_context(self, *, signup_form=None, highlighted_subscription=None, preference_form_errors=None):
        subscriptions = list(
            UserSubscription.objects.filter(user=self.request.user).select_related("plan", "latest_order")
        )
        return {
            "subscription_rows": [
                {
                    "subscription": subscription,
                    "preferences_form": preference_form_errors.get(subscription.pk)
                    if preference_form_errors and subscription.pk in preference_form_errors
                    else SubscriptionPreferencesForm(instance=subscription),
                    "is_highlighted": highlighted_subscription is not None and subscription.pk == highlighted_subscription.pk,
                }
                for subscription in subscriptions
            ],
            "next_shipment": next(
                (
                    subscription
                    for subscription in sorted(
                        [item for item in subscriptions if item.status == UserSubscription.Status.ACTIVE],
                        key=lambda item: item.next_shipment_date or date.max,
                    )
                ),
                None,
            ),
            "highlighted_subscription": highlighted_subscription,
            "signup_form": signup_form or SubscriptionSignupForm(),
            "dashboard_empty_state_title": "No active subscriptions yet.",
            "dashboard_empty_state_body": "Start with a curated Nest & Whisk plan and we’ll help you settle into your ideal cookie rhythm.",
        }

    def form_valid(self, form):
        plan = form.cleaned_data["plan"]
        preferences = [item.strip() for item in form.cleaned_data.get("flavor_preferences", "").split(",") if item.strip()]
        renewal_day = form.cleaned_data["renewal_day"]
        existing_subscription = UserSubscription.objects.filter(
            user=self.request.user,
            plan=plan,
            status__in=[
                UserSubscription.Status.ACTIVE,
                UserSubscription.Status.PAUSED,
                UserSubscription.Status.PAST_DUE,
            ],
        ).first()
        if existing_subscription:
            if existing_subscription.status == UserSubscription.Status.PAUSED:
                existing_subscription.status = UserSubscription.Status.ACTIVE
                existing_subscription.paused_from = None
                if preferences:
                    existing_subscription.flavor_preferences = preferences
                existing_subscription.renewal_day = renewal_day
                existing_subscription.refresh_schedule()
                existing_subscription.save(
                    update_fields=[
                        "status",
                        "paused_from",
                        "flavor_preferences",
                        "renewal_day",
                        "next_renewal_date",
                        "next_shipment_date",
                        "updated_at",
                    ]
                )
                messages.success(
                    self.request,
                    f"{plan.name} was already paused, so we resumed it. Your next renewal is set for {existing_subscription.next_renewal_date} and your next shipment is penciled in for {existing_subscription.next_shipment_date}.",
                )
                return redirect(f"{reverse('subscriptions:dashboard')}?highlight={existing_subscription.pk}")

            messages.info(
                self.request,
                f"You already have {plan.name} on your subscription dashboard. Update its preferences or billing rhythm below instead of creating a duplicate.",
            )
            return redirect(f"{reverse('subscriptions:dashboard')}?highlight={existing_subscription.pk}")

        subscription = UserSubscription(
            user=self.request.user,
            plan=plan,
            flavor_preferences=preferences,
            renewal_day=renewal_day,
        )
        subscription.refresh_schedule()
        subscription.save()
        messages.success(
            self.request,
            f"{plan.name} has been added to your subscription dashboard. Your next renewal is set for {subscription.next_renewal_date} and your first shipment is targeted for {subscription.next_shipment_date}.",
        )
        return redirect(f"{reverse('subscriptions:dashboard')}?highlight={subscription.pk}")

    def form_invalid(self, form):
        context = self._build_dashboard_context(signup_form=form)
        context.update(super().get_context_data(form=form))
        return self.render_to_response(context)


class SubscriptionDashboardView(LoginRequiredMixin, CoreContextMixin, TemplateView):
    template_name = "subscriptions/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        subscriptions = list(
            UserSubscription.objects.filter(user=self.request.user).select_related("plan", "latest_order")
        )
        highlight_pk = self.request.GET.get("highlight")
        highlighted_subscription = None
        if highlight_pk and highlight_pk.isdigit():
            highlighted_subscription = next(
                (subscription for subscription in subscriptions if subscription.pk == int(highlight_pk)),
                None,
            )

        context["subscription_rows"] = [
            {
                "subscription": subscription,
                "preferences_form": SubscriptionPreferencesForm(instance=subscription),
                "is_highlighted": highlighted_subscription is not None and subscription.pk == highlighted_subscription.pk,
            }
            for subscription in subscriptions
        ]
        context["next_shipment"] = next(
            (
                subscription
                for subscription in sorted(
                    [item for item in subscriptions if item.status == UserSubscription.Status.ACTIVE],
                    key=lambda item: item.next_shipment_date or date.max,
                )
            ),
            None,
        )
        context["highlighted_subscription"] = highlighted_subscription
        context["signup_form"] = SubscriptionSignupForm()
        context["dashboard_empty_state_title"] = "No active subscriptions yet."
        context["dashboard_empty_state_body"] = "Start with a curated Nest & Whisk plan and we’ll help you settle into your ideal cookie rhythm."
        return context


class SubscriptionPreferencesUpdateView(LoginRequiredMixin, View):
    http_method_names = ["post"]

    def _build_dashboard_context(self, *, request, bound_form, highlighted_subscription):
        subscriptions = list(
            UserSubscription.objects.filter(user=request.user).select_related("plan", "latest_order")
        )
        return {
            "subscription_rows": [
                {
                    "subscription": subscription,
                    "preferences_form": bound_form if subscription.pk == highlighted_subscription.pk else SubscriptionPreferencesForm(instance=subscription),
                    "is_highlighted": subscription.pk == highlighted_subscription.pk,
                }
                for subscription in subscriptions
            ],
            "next_shipment": next(
                (
                    subscription
                    for subscription in sorted(
                        [item for item in subscriptions if item.status == UserSubscription.Status.ACTIVE],
                        key=lambda item: item.next_shipment_date or date.max,
                    )
                ),
                None,
            ),
            "highlighted_subscription": highlighted_subscription,
            "signup_form": SubscriptionSignupForm(),
            "dashboard_empty_state_title": "No active subscriptions yet.",
            "dashboard_empty_state_body": "Start with a curated Nest & Whisk plan and we’ll help you settle into your ideal cookie rhythm.",
        }

    def post(self, request, pk):
        subscription = get_object_or_404(UserSubscription, pk=pk, user=request.user)
        if subscription.status == UserSubscription.Status.CANCELLED:
            messages.info(request, "Cancelled subscriptions can’t be edited here. Start a fresh plan from the sidebar instead.")
            return redirect(f"{reverse('subscriptions:dashboard')}?highlight={subscription.pk}")

        form = SubscriptionPreferencesForm(request.POST, instance=subscription)
        if form.is_valid():
            updated_subscription = form.save(commit=False)
            updated_subscription.refresh_schedule()
            updated_subscription.save()
            messages.success(request, "Your subscription preferences have been updated.")
            return redirect(f"{reverse('subscriptions:dashboard')}?highlight={subscription.pk}")

        messages.error(request, "We couldn't update those preferences. Please review the highlighted form and try again.")
        view = SubscriptionDashboardView()
        view.request = request
        context = view.get_context_data()
        context.update(self._build_dashboard_context(request=request, bound_form=form, highlighted_subscription=subscription))
        return view.render_to_response(context)


class SubscriptionPauseView(LoginRequiredMixin, View):
    http_method_names = ["post"]

    def post(self, request, pk):
        subscription = get_object_or_404(UserSubscription, pk=pk, user=request.user)
        if subscription.status == UserSubscription.Status.CANCELLED:
            messages.info(request, "This subscription is already cancelled and can’t be paused.")
            return redirect(f"{reverse('subscriptions:dashboard')}?highlight={subscription.pk}")
        if subscription.status == UserSubscription.Status.PAUSED:
            messages.info(request, "This subscription is already paused.")
            return redirect(f"{reverse('subscriptions:dashboard')}?highlight={subscription.pk}")

        subscription.status = UserSubscription.Status.PAUSED
        subscription.paused_from = date.today()
        subscription.save(update_fields=["status", "paused_from", "updated_at"])
        messages.success(request, f"{subscription.plan.name} has been paused. We’ll hold future renewals until you resume it.")
        return redirect(f"{reverse('subscriptions:dashboard')}?highlight={subscription.pk}")


class SubscriptionResumeView(LoginRequiredMixin, View):
    http_method_names = ["post"]

    def post(self, request, pk):
        subscription = get_object_or_404(UserSubscription, pk=pk, user=request.user)
        if subscription.status == UserSubscription.Status.CANCELLED:
            messages.info(request, "Cancelled subscriptions can’t be resumed. Start a fresh subscription instead.")
            return redirect(f"{reverse('subscriptions:dashboard')}?highlight={subscription.pk}")
        if subscription.status == UserSubscription.Status.ACTIVE:
            messages.info(request, "This subscription is already active.")
            return redirect(f"{reverse('subscriptions:dashboard')}?highlight={subscription.pk}")

        subscription.status = UserSubscription.Status.ACTIVE
        subscription.paused_from = None
        subscription.refresh_schedule()
        subscription.save(update_fields=["status", "paused_from", "next_renewal_date", "next_shipment_date", "updated_at"])
        messages.success(request, f"{subscription.plan.name} has been resumed and is back on its recurring rhythm.")
        return redirect(f"{reverse('subscriptions:dashboard')}?highlight={subscription.pk}")


class SubscriptionCancelView(LoginRequiredMixin, View):
    http_method_names = ["post"]

    def post(self, request, pk):
        subscription = get_object_or_404(UserSubscription, pk=pk, user=request.user)
        if subscription.status == UserSubscription.Status.CANCELLED:
            messages.info(request, "This subscription is already cancelled.")
            return redirect(f"{reverse('subscriptions:dashboard')}?highlight={subscription.pk}")

        subscription.status = UserSubscription.Status.CANCELLED
        subscription.cancelled_at = subscription.updated_at
        subscription.save(update_fields=["status", "cancelled_at", "updated_at"])
        messages.success(request, f"{subscription.plan.name} has been cancelled. You can start a fresh plan anytime from the dashboard.")
        return redirect(f"{reverse('subscriptions:dashboard')}?highlight={subscription.pk}")
