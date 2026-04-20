from html import unescape
import json

import pytest
from django.test import override_settings
from django.urls import reverse

from apps.catalog.models import DietaryAttribute, Product, ProductCategory, ProductVariant
from apps.core.models import FAQ, PolicyPage
from apps.core import services
from apps.core.services import answer_support_question
from apps.subscriptions.models import SubscriptionPlan


@pytest.mark.django_db
def test_answer_support_question_prefers_matching_faq_content():
    FAQ.objects.create(
        question="How fresh are your cookies when they arrive?",
        answer="They are baked in small batches and packed shortly before dispatch.",
        category="Freshness",
        is_published=True,
        sort_order=1,
    )

    result = answer_support_question("Will my cookies arrive fresh?")

    assert "packed shortly before dispatch" in result.answer
    assert result.source_type == "FAQ"
    assert result.source_title == "How fresh are your cookies when they arrive?"


@pytest.mark.django_db
def test_answer_support_question_can_fall_back_to_policies():
    PolicyPage.objects.create(
        title="Shipping & Delivery",
        slug="shipping-delivery",
        summary="Delivery timing guidance.",
        body="Orders usually ship within two business days and arrive in carefully protected packaging.",
        is_published=True,
    )

    result = answer_support_question("How long does shipping take?")

    assert "two business days" in result.answer
    assert result.source_type == "Policy"


@pytest.mark.django_db
def test_answer_support_question_uses_active_product_knowledge():
    category = ProductCategory.objects.create(name="Signature Cookies", slug="signature-cookies")
    dietary = DietaryAttribute.objects.create(name="Vegetarian", slug="vegetarian")
    product = Product.objects.create(
        category=category,
        name="Sea Salt Caramel",
        slug="sea-salt-caramel",
        short_description="Buttery caramel cookie with a glossy sea salt finish.",
        description="A rich caramel-forward cookie finished with flaky sea salt.",
        ingredients="Butter, flour, caramel, sea salt",
        allergen_information="Contains wheat and dairy",
        is_active=True,
    )
    product.dietary_attributes.add(dietary)
    ProductVariant.objects.create(
        product=product,
        name="Box of 6",
        sku="SSC-6",
        pack_size=6,
        price="799.00",
        inventory_quantity=12,
        is_active=True,
    )

    result = answer_support_question("Tell me about your sea salt caramel cookies")

    assert result.source_type == "Product"
    assert result.source_title == "Sea Salt Caramel"
    assert "caramel-forward cookie" in result.answer
    assert "₹799.00" in result.answer or "₹799" in result.answer
    assert result.cta_url == product.get_absolute_url()


@pytest.mark.django_db
def test_answer_support_question_excludes_inactive_products():
    category = ProductCategory.objects.create(name="Seasonal", slug="seasonal")
    Product.objects.create(
        category=category,
        name="Pumpkin Spice",
        slug="pumpkin-spice",
        short_description="Seasonal cookie",
        description="Warm spice cookie for autumn.",
        is_active=False,
    )

    result = answer_support_question("Do you have pumpkin spice cookies?")

    assert result.source_title != "Pumpkin Spice"
    assert result.source_type != "Product"


@pytest.mark.django_db
def test_answer_support_question_uses_subscription_plan_knowledge():
    plan = SubscriptionPlan.objects.create(
        name="Monthly Cookie Ritual",
        slug="monthly-cookie-ritual",
        headline="A rotating monthly box of favorites.",
        description="Perfect for gifting or keeping your cookie drawer stocked.",
        billing_interval=SubscriptionPlan.BillingInterval.MONTHLY,
        cadence_days=30,
        shipment_offset_days=5,
        box_size="12 cookies",
        price="1899.00",
        compare_at_price="2099.00",
        is_active=True,
        is_featured=True,
    )

    result = answer_support_question("What does your monthly subscription include?")

    assert result.source_type == "Subscription"
    assert result.source_title == "Monthly Cookie Ritual"
    assert "12 cookies" in result.answer
    assert "every 30 days" in result.answer
    assert result.cta_url == plan.get_absolute_url()


@pytest.mark.django_db
@override_settings(
    AI_CHAT_ENABLED=True,
    AI_CHAT_API_KEY="test-key",
    AI_CHAT_MODEL="gpt-4.1-mini",
)
def test_answer_support_question_can_return_ai_assisted_response(monkeypatch):
    FAQ.objects.create(
        question="Do you offer recurring subscription boxes?",
        answer="Yes, we offer weekly, biweekly, and monthly plans.",
        category="Subscriptions",
        is_published=True,
        sort_order=1,
    )

    monkeypatch.setattr(
        "apps.core.services._request_ai_completion",
        lambda **kwargs: "Yes — we offer weekly, biweekly, and monthly subscription boxes with flexible timing.",
    )

    result = answer_support_question("Do you have subscriptions?")

    assert result.used_ai is True
    assert result.model_name == "gpt-4.1-mini"
    assert "weekly, biweekly, and monthly subscription boxes" in result.answer
    assert result.source_type == "AI-assisted support"


@pytest.mark.django_db
@override_settings(
    AI_CHAT_ENABLED=True,
    AI_CHAT_PROVIDER="gemini",
    AI_CHAT_API_KEY="gemini-test-key",
    AI_CHAT_MODEL="gemini-2.0-flash",
    AI_CHAT_BASE_URL="https://generativelanguage.googleapis.com/v1beta",
)
def test_request_ai_completion_supports_gemini_payload(monkeypatch):
    captured = {}

    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(
                {
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {"text": "Gemini grounded answer."},
                                ]
                            }
                        }
                    ]
                }
            ).encode("utf-8")

    def fake_urlopen(req, timeout):
        captured["url"] = req.full_url
        captured["body"] = json.loads(req.data.decode("utf-8"))
        captured["timeout"] = timeout
        return _FakeResponse()

    monkeypatch.setattr(services.request, "urlopen", fake_urlopen)

    response = services._request_ai_completion(
        messages=[
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "Tell me about subscriptions"},
        ]
    )

    assert response == "Gemini grounded answer."
    assert ":generateContent?key=gemini-test-key" in captured["url"]
    assert captured["body"]["systemInstruction"]["parts"][0]["text"] == "System prompt"
    assert captured["body"]["contents"][0]["parts"][0]["text"] == "Tell me about subscriptions"


@pytest.mark.django_db
def test_faq_assistant_endpoint_returns_json_answer(client):
    FAQ.objects.create(
        question="Do you offer recurring subscription boxes?",
        answer="Yes, we offer weekly, biweekly, and monthly plans.",
        category="Subscriptions",
        is_published=True,
        sort_order=1,
    )

    response = client.get(reverse("faq_assistant"), {"question": "Do you have subscriptions?"})
    payload = response.json()

    assert response.status_code == 200
    assert payload["ok"] is True
    assert "weekly, biweekly, and monthly plans" in payload["answer"]
    assert payload["source_type"] == "FAQ"


@pytest.mark.django_db
def test_faq_page_renders_existing_questions(client):
    FAQ.objects.create(
        question="Can I choose my own flavors in a gift box?",
        answer="Yes. Use build-a-box to curate your own assortment.",
        category="Ordering",
        is_published=True,
        sort_order=1,
    )

    response = client.get(reverse("faq"))
    content = unescape(response.content.decode())

    assert response.status_code == 200
    assert "Everything you’d want to know before the first bite." in content
    assert "Can I choose my own flavors in a gift box?" in content
    assert 'data-faq-assistant' in content
    assert reverse("faq_assistant") in content


