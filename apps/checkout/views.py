from django.contrib import messages
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import FormView, TemplateView, View

import stripe

from apps.cart.services import get_or_create_cart
from apps.checkout.emailing import build_tracking_link_payloads, send_tracking_links_email
from apps.checkout.forms import CheckoutForm, OrderLookupForm, TrackingLinkRequestForm
from apps.checkout.shiprocket import get_checkout_delivery_experience
from apps.checkout.services import (
    MockPaymentConfigurationError,
    StripeCheckoutConfigurationError,
    StripeWebhookConfigurationError,
    apply_mock_payment_outcome,
    construct_stripe_event,
    create_stripe_checkout_session,
    handle_stripe_event,
)
from apps.checkout.tasks import enqueue_tracking_link_payloads
from apps.core.views import CoreContextMixin
from apps.orders.models import Order
from apps.orders.services import create_order_from_cart


class CheckoutView(CoreContextMixin, FormView):
    template_name = "checkout/checkout.html"
    form_class = CheckoutForm

    def get_delivery_experience(self, form=None):
        city = ""
        postal_code = ""
        if form is not None:
            city = form.data.get("shipping_city") or form.initial.get("shipping_city", "")
            postal_code = form.data.get("shipping_postal_code") or form.initial.get("shipping_postal_code", "")
        else:
            initial = self.get_initial()
            city = initial.get("shipping_city", "")
            postal_code = initial.get("shipping_postal_code", "")
        return get_checkout_delivery_experience(city=city, postal_code=postal_code)

    def upi_enabled(self) -> bool:
        return settings.STRIPE_ENABLE_UPI and settings.STRIPE_CURRENCY.lower() == "inr"

    def mock_enabled(self) -> bool:
        return settings.MOCK_PAYMENT_ENABLED

    def get_cart(self):
        session_key = self.request.session.session_key
        if not session_key:
            self.request.session.create()
            session_key = self.request.session.session_key
        return get_or_create_cart(user=self.request.user, session_key=session_key or "")

    def get_initial(self):
        initial = super().get_initial()
        user = self.request.user
        if user.is_authenticated:
            initial.update(
                {
                    "customer_email": user.email,
                    "customer_first_name": user.first_name,
                    "customer_last_name": user.last_name,
                    "customer_phone": user.phone_number,
                }
            )
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["allow_upi"] = self.upi_enabled()
        kwargs["allow_mock"] = self.mock_enabled()
        kwargs["default_payment_provider"] = settings.DEFAULT_PAYMENT_PROVIDER
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cart"] = self.get_cart()
        context["upi_enabled"] = self.upi_enabled()
        context["mock_payment_enabled"] = self.mock_enabled()
        context["store_currency"] = settings.STRIPE_CURRENCY.upper()
        context["delivery_experience"] = self.get_delivery_experience(context.get("form"))
        return context

    def form_valid(self, form):
        cart = self.get_cart()
        if cart.item_count == 0:
            messages.error(self.request, "Your cart is empty. Add something sweet before checkout.")
            return redirect("cart:detail")
        order = create_order_from_cart(
            cart=cart,
            checkout_data=form.cleaned_data,
            user=self.request.user,
        )
        messages.success(self.request, f"Order {order.order_number} created. Payment is the next step.")
        return redirect(reverse("checkout:success", kwargs={"order_number": order.order_number}))


class CheckoutStartPaymentView(CoreContextMixin, View):
    http_method_names = ["post"]

    def post(self, request, order_number):
        order = get_object_or_404(Order.objects.prefetch_related("payments", "items"), order_number=order_number)
        payment = order.payments.order_by("-created_at").first()
        if payment is None:
            messages.error(request, "No payment record is available for this order yet.")
            return redirect("checkout:success", order_number=order.order_number)

        if payment.provider == "mock":
            if not settings.MOCK_PAYMENT_ENABLED:
                messages.error(request, "Mock payment mode is not enabled in this environment.")
                return redirect("checkout:success", order_number=order.order_number)
            return redirect("checkout:mock_payment", order_number=order.order_number)
        if payment.provider != "stripe":
            messages.error(request, f"Unsupported payment provider '{payment.provider}'.")
            return redirect("checkout:success", order_number=order.order_number, state="failed")

        try:
            checkout_url = create_stripe_checkout_session(order=order, payment=payment, request=request)
        except StripeCheckoutConfigurationError as exc:
            messages.error(request, str(exc))
            return redirect("checkout:success", order_number=order.order_number)
        except stripe.StripeError as exc:
            messages.error(request, f"Stripe could not start checkout: {exc.user_message or str(exc)}")
            return redirect("checkout:success", order_number=order.order_number, state="failed")

        return redirect(checkout_url)


class MockPaymentView(CoreContextMixin, TemplateView):
    template_name = "checkout/mock_payment.html"

    def get_order(self):
        return Order.objects.prefetch_related("payments", "items").get(order_number=self.kwargs["order_number"])

    def dispatch(self, request, *args, **kwargs):
        if not settings.MOCK_PAYMENT_ENABLED:
            messages.error(request, "Mock payment mode is not enabled in this environment.")
            return redirect("checkout:index")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = self.get_order()
        payment = order.payments.order_by("-created_at").first()
        context.update(
            {
                "order": order,
                "payment": payment,
                "success_url": reverse("checkout:success", kwargs={"order_number": order.order_number}),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        order = self.get_order()
        payment = order.payments.order_by("-created_at").first()
        if payment is None:
            messages.error(request, "No payment record is available for this order yet.")
            return redirect("checkout:success", order_number=order.order_number)

        outcome = request.POST.get("outcome", "").strip().lower()
        try:
            apply_mock_payment_outcome(payment=payment, outcome=outcome)
        except MockPaymentConfigurationError as exc:
            messages.error(request, str(exc))
            return redirect("checkout:mock_payment", order_number=order.order_number)

        state_map = {
            "success": "",
            "failed": "failed",
            "cancelled": "cancelled",
        }
        if outcome == "success":
            messages.success(request, f"Mock payment marked as paid for order {order.order_number}.")
        elif outcome == "failed":
            messages.warning(request, f"Mock payment marked as failed for order {order.order_number}.")
        else:
            messages.info(request, f"Mock payment marked as cancelled for order {order.order_number}.")

        target = reverse("checkout:success", kwargs={"order_number": order.order_number})
        state = state_map.get(outcome, "")
        if state:
            target = f"{target}?state={state}"
        return redirect(target)


@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(View):
    http_method_names = ["post"]

    def post(self, request):
        signature = request.META.get("HTTP_STRIPE_SIGNATURE", "")
        try:
            event = construct_stripe_event(payload=request.body, signature=signature)
        except StripeWebhookConfigurationError as exc:
            return HttpResponse(str(exc), status=500)
        except ValueError:
            return HttpResponse("Invalid payload", status=400)
        except stripe.error.SignatureVerificationError:
            return HttpResponse("Invalid signature", status=400)

        handle_stripe_event(event)
        return HttpResponse(status=200)


class CheckoutCancelledView(View):
    def get(self, request, order_number):
        return redirect("checkout:success", order_number=order_number, state="cancelled")


class DeliveryEstimateLookupView(View):
    http_method_names = ["get"]

    def get(self, request):
        city = request.GET.get("city", "")
        postal_code = request.GET.get("postal_code", "")
        experience = get_checkout_delivery_experience(city=city, postal_code=postal_code)
        return JsonResponse(
            {
                "ok": True,
                **experience,
            }
        )


class CheckoutSuccessView(CoreContextMixin, TemplateView):
    template_name = "checkout/success.html"

    RETRYABLE_PAYMENT_STATUSES = {"pending", "requires_action", "failed", "cancelled"}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = Order.objects.prefetch_related("payments", "items").get(order_number=self.kwargs["order_number"])
        payment = order.payments.first()
        payment_preferences = payment.raw_response.get("checkout_preferences", {}) if payment and isinstance(payment.raw_response, dict) else {}
        state = self.request.GET.get("state", "")

        if not state and payment and payment.provider_reference == "expired":
            state = "expired"
        elif not state and payment and payment.status == "cancelled":
            state = "cancelled"

        state_messages = {
            "cancelled": {
                "eyebrow": "Payment cancelled",
                "title": "Your payment was cancelled before it completed.",
                "body": "Your order is still saved, and you can resume secure payment whenever you're ready.",
                "notice": "No payment was captured for this attempt.",
            },
            "expired": {
                "eyebrow": "Session expired",
                "title": "Your previous payment session expired.",
                "body": "No worries—your order is still waiting, and you can start a fresh secure payment session below.",
                "notice": "Expired sessions stay safely retryable from this page.",
            },
            "failed": {
                "eyebrow": "Payment needs attention",
                "title": "Your order is saved, but payment needs another try.",
                "body": "We couldn’t complete payment for this order. Review your details and retry securely when you're ready.",
                "notice": payment.provider_reference if payment and payment.provider_reference else "Your bank or wallet declined the previous attempt.",
            },
        }

        if order.payment_status == Order.PaymentStatus.PAID:
            hero = {
                "eyebrow": "Payment received",
                "title": "Payment received. Your cookies are officially in motion.",
                "body": "We’ve received your payment and your order is now moving into preparation. You’ll see the latest status updates here as Batch 6 expands.",
                "notice": "A confirmed payment record is now attached to your order.",
            }
        elif order.payment_status == Order.PaymentStatus.REFUNDED:
            hero = {
                "eyebrow": "Payment refunded",
                "title": "This payment has been refunded.",
                "body": "Your order and payment record are still available here for reference.",
                "notice": payment.provider_reference if payment and payment.provider_reference else "Refund details are recorded in your payment history.",
            }
        elif state in state_messages:
            hero = state_messages[state]
        elif payment and payment.provider == "mock":
            hero = {
                "eyebrow": "Mock payment ready",
                "title": "Your order is ready for local payment simulation.",
                "body": "Use the mock simulator to mark this order as paid, failed, or cancelled while you test the Nest & Whisk payment lifecycle locally.",
                "notice": "Mock mode updates the same order and payment states used by the real checkout flow.",
            }
        else:
            hero = {
                "eyebrow": "Awaiting payment",
                "title": "Your order is ready for payment.",
                "body": "Your order has been created and is waiting for secure payment confirmation through Stripe. If your session expires, you can retry from this screen.",
                "notice": "Webhook updates will refresh the payment and order status behind the scenes.",
            }

        context.update(
            {
                "order": order,
                "payment": payment,
                "payment_preferences": payment_preferences,
                "hero": hero,
                "can_retry_payment": bool(payment and payment.status in self.RETRYABLE_PAYMENT_STATUSES),
                "retry_button_label": (
                    "Open mock payment simulator"
                    if payment and payment.provider == "mock"
                    else "Retry secure payment" if payment and payment.status == "failed" else "Continue to secure payment"
                ),
                "tracking_url": reverse("checkout:tracking", kwargs={"order_number": order.order_number}),
            }
        )
        return context


class OrderLookupView(CoreContextMixin, FormView):
    template_name = "checkout/tracking.html"
    form_class = OrderLookupForm
    throttle_key = "checkout_order_lookup_attempts"
    throttle_limit = 5
    throttle_window_seconds = 900

    def get_recent_attempts(self):
        timestamps = self.request.session.get(self.throttle_key, [])
        now = timezone.now().timestamp()
        window_start = now - self.throttle_window_seconds
        return [ts for ts in timestamps if ts >= window_start]

    def record_attempt(self):
        attempts = self.get_recent_attempts()
        attempts.append(timezone.now().timestamp())
        self.request.session[self.throttle_key] = attempts
        self.request.session.modified = True

    def is_throttled(self):
        return len(self.get_recent_attempts()) >= self.throttle_limit

    def get_lockout_seconds_remaining(self):
        attempts = self.get_recent_attempts()
        if not attempts:
            return 0
        oldest_relevant = min(attempts)
        unlock_at = oldest_relevant + self.throttle_window_seconds
        return max(0, int(unlock_at - timezone.now().timestamp()))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        if getattr(user, "is_authenticated", False):
            lookup_help = "You're signed in, so you can jump between orders using your order number and email for guest-friendly tracking links."
        else:
            lookup_help = "Use the order number from your confirmation email and the same email address used at checkout."
        context.setdefault("lookup_form", context.get("form"))
        context.setdefault("link_request_form", TrackingLinkRequestForm())
        context.setdefault("lookup_help", lookup_help)
        context.setdefault("lookup_recovery_tip", "If payment is still pending after lookup, you can continue or retry securely from the order summary.")
        context.setdefault("lockout_message", "")
        return context

    def form_valid(self, form):
        if self.is_throttled():
            remaining = self.get_lockout_seconds_remaining()
            minutes = max(1, (remaining + 59) // 60)
            form.add_error(None, f"Too many lookup attempts from this browser. Please wait about {minutes} minute(s) before trying again.")
            context = self.get_context_data(form=form)
            context["lockout_message"] = f"Lookup is temporarily locked to protect customer orders. Try again in about {minutes} minute(s), or request your tracking links by email below."
            return self.render_to_response(context)

        self.record_attempt()
        order = Order.objects.filter(
            order_number=form.cleaned_data["order_number"].strip().upper(),
            customer_email__iexact=form.cleaned_data["customer_email"],
        ).first()
        if not order:
            form.add_error(None, "We couldn't find an order matching that number and email address. Double-check your confirmation email and try again.")
            context = self.get_context_data(form=form)
            context["lockout_message"] = "Still stuck? Use the email option below and we’ll send your matching tracking links if we find an order for that inbox."
            return self.render_to_response(context)
        return redirect("checkout:tracking", order_number=order.order_number)


class TrackingLinkRequestView(CoreContextMixin, FormView):
    template_name = "checkout/tracking.html"
    form_class = TrackingLinkRequestForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("lookup_form", OrderLookupForm())
        context.setdefault("link_request_form", context.get("form"))
        context.setdefault("lookup_help", "If you no longer have your order number, request your tracking links by email.")
        context.setdefault("lookup_recovery_tip", "We’ll send links for matching orders to the email address you enter below.")
        return context

    def form_valid(self, form):
        orders = list(Order.objects.filter(customer_email__iexact=form.cleaned_data["customer_email"]).order_by("-created_at")[:5])
        payloads = build_tracking_link_payloads(orders=orders, request=self.request)
        if payloads:
            try:
                enqueue_tracking_link_payloads(payloads)
            except Exception:
                for order in orders:
                    send_tracking_links_email(order=order, request=self.request)
        messages.success(self.request, "If we found matching orders for that email address, we’ve sent tracking links to the inbox used at checkout.")
        return redirect("checkout:lookup")


class OrderTrackingView(CoreContextMixin, TemplateView):
    template_name = "checkout/tracking.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = Order.objects.prefetch_related("payments", "items").get(order_number=self.kwargs["order_number"])
        payment = order.payments.first()
        timeline = [
            {
                "label": "Order placed",
                "value": order.placed_at or order.created_at,
                "detail": "Your order has been created and saved.",
            },
            {
                "label": "Payment state",
                "value": payment.paid_at if payment and payment.paid_at else order.updated_at,
                "detail": f"Current payment status: {payment.get_status_display() if payment else 'Pending'}.",
            },
            {
                "label": "Order state",
                "value": order.updated_at,
                "detail": f"Current order status: {order.get_status_display()}.",
            },
        ]
        context.update(
            {
                "order": order,
                "payment": payment,
                "timeline": timeline,
                "lookup_form": OrderLookupForm(initial={"order_number": order.order_number, "customer_email": order.customer_email}),
                "link_request_form": TrackingLinkRequestForm(initial={"customer_email": order.customer_email}),
                "lookup_help": "Need another status refresh? Re-enter the same order number and email to jump between orders.",
                "lookup_recovery_tip": "If payment is still pending or failed, return to the payment summary to retry securely.",
                "lockout_message": "",
            }
        )
        return context
