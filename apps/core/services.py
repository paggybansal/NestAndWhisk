from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from urllib import error, request

from django.conf import settings

from apps.catalog.models import Product, ProductVariant
from apps.core.models import FAQ, ContactSettings, PolicyPage
from apps.subscriptions.models import SubscriptionPlan

logger = logging.getLogger(__name__)

_WORD_RE = re.compile(r"[a-z0-9']+")
_STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "about",
    "can",
    "do",
    "for",
    "from",
    "how",
    "i",
    "in",
    "is",
    "me",
    "my",
    "of",
    "on",
    "or",
    "the",
    "to",
    "we",
    "what",
    "when",
    "with",
    "you",
    "your",
}


@dataclass(slots=True)
class SupportAnswer:
    answer: str
    source_title: str
    source_type: str
    follow_up_questions: list[str]
    confidence: float
    used_ai: bool = False
    model_name: str = ""
    cta_label: str = "Still need help? Contact our team"
    cta_url: str = "/contact/"


@dataclass(slots=True)
class _KnowledgeItem:
    title: str
    body: str
    category: str
    source_type: str
    url: str


_DEFAULT_FALLBACK_QUESTIONS = [
    "How fresh are your cookies when they arrive?",
    "Can I choose my own flavors in a gift box?",
    "Do you offer recurring subscription boxes?",
]


def _tokenize(text: str) -> set[str]:
    return {
        token
        for token in _WORD_RE.findall((text or "").lower())
        if token not in _STOP_WORDS and len(token) > 1
    }


def _score_item(query: str, query_tokens: set[str], item: _KnowledgeItem) -> float:
    haystack = f"{item.title} {item.category} {item.body}".lower()
    title_tokens = _tokenize(item.title)
    category_tokens = _tokenize(item.category)
    haystack_tokens = _tokenize(haystack)

    overlap = len(query_tokens & haystack_tokens)
    title_overlap = len(query_tokens & title_tokens)
    category_overlap = len(query_tokens & category_tokens)
    phrase_ratio = SequenceMatcher(None, query.lower(), haystack).ratio()

    score = (overlap * 2.4) + (title_overlap * 2.8) + (category_overlap * 1.5) + (phrase_ratio * 3.5)
    if query.lower() in haystack:
        score += 2.5
    return score


def _build_knowledge_items() -> list[_KnowledgeItem]:
    items: list[_KnowledgeItem] = []
    for faq in FAQ.objects.filter(is_published=True):
        items.append(
            _KnowledgeItem(
                title=faq.question,
                body=faq.answer,
                category=faq.category,
                source_type="FAQ",
                url="/faq/",
            )
        )

    for policy in PolicyPage.objects.filter(is_published=True):
        items.append(
            _KnowledgeItem(
                title=policy.title,
                body=f"{policy.summary} {policy.body}".strip(),
                category="Policies",
                source_type="Policy",
                url=f"/policies/{policy.slug}/",
            )
        )

    contact_settings = ContactSettings.load()
    items.append(
        _KnowledgeItem(
            title="How can I contact Nest & Whisk support?",
            body=(
                f"You can reach our team at {contact_settings.inquiry_email}. "
                f"Business hours are {contact_settings.business_hours}. {contact_settings.contact_card_body}"
            ),
            category="Contact",
            source_type="Contact",
            url="/contact/",
        )
    )

    product_queryset = Product.objects.filter(is_active=True).select_related("category").prefetch_related(
        "dietary_attributes",
    )
    for product in product_queryset:
        variant_summaries = []
        active_variants = list(ProductVariant.objects.filter(product=product, is_active=True).order_by("sort_order", "price")[:4])
        for variant in active_variants[:4]:
            stock_text = "in stock" if variant.is_in_stock else "currently out of stock"
            variant_summaries.append(
                f"{variant.name} ({variant.pack_size} cookies) for ₹{variant.price} — {stock_text}"
            )

        dietary_labels = [item.badge_label or item.name for item in product.dietary_attributes.all()]
        dietary_text = ", ".join(dietary_labels) if dietary_labels else "No dietary badges listed"
        build_a_box_text = "Available in build-a-box assortments." if product.allows_build_a_box else "Not part of build-a-box assortments."
        ingredient_highlights = ", ".join(product.ingredient_highlight_items)
        texture_text = ", ".join(
            f"{item['label']} {item['score']}/5" for item in product.texture_meter_items
        )
        pairing_text = ", ".join(item["label"] for item in product.pairing_items)

        product_body = " ".join(
            part
            for part in [
                f"Product category: {product.category.name}.",
                product.short_description,
                product.description,
                f"Ingredient highlights: {ingredient_highlights}." if ingredient_highlights else "",
                f"Ingredients: {product.ingredients}." if product.ingredients else "",
                f"Allergens: {product.allergen_information}." if product.allergen_information else "",
                f"Nutritional notes: {product.nutritional_notes}." if product.nutritional_notes else "",
                f"Care instructions: {product.care_instructions}." if product.care_instructions else "",
                f"Shelf life: {product.shelf_life_display}.",
                f"Storage guidance: {product.storage_guidance_display}.",
                f"Texture profile: {texture_text}.",
                f"Recommended pairings: {pairing_text}." if pairing_text else "",
                f"Dietary attributes: {dietary_text}.",
                build_a_box_text,
                f"Variants: {'; '.join(variant_summaries)}." if variant_summaries else "Currently no active variants are listed.",
            ]
            if part
        )

        items.append(
            _KnowledgeItem(
                title=product.name,
                body=product_body,
                category=f"Product · {product.category.name}",
                source_type="Product",
                url=product.get_absolute_url(),
            )
        )

    for plan in SubscriptionPlan.objects.filter(is_active=True):
        billing_interval_labels = {
            SubscriptionPlan.BillingInterval.WEEKLY: "Weekly",
            SubscriptionPlan.BillingInterval.BIWEEKLY: "Biweekly",
            SubscriptionPlan.BillingInterval.MONTHLY: "Monthly",
        }
        compare_text = (
            f"Compare-at price: ₹{plan.compare_at_price}."
            if plan.compare_at_price and plan.compare_at_price > plan.price
            else ""
        )
        plan_body = " ".join(
            part
            for part in [
                plan.headline,
                plan.description,
                f"Billing interval: {billing_interval_labels.get(plan.billing_interval, plan.billing_interval)}.",
                f"Cadence: every {plan.cadence_days} days.",
                f"Ships {plan.shipment_offset_days} days after renewal.",
                f"Box size: {plan.box_size}.",
                f"Price: ₹{plan.price} per renewal.",
                compare_text,
                "Featured plan." if plan.is_featured else "",
            ]
            if part
        )
        items.append(
            _KnowledgeItem(
                title=plan.name,
                body=plan_body,
                category="Subscription plan",
                source_type="Subscription",
                url=plan.get_absolute_url(),
            )
        )

    return items


def _rank_knowledge_items(question: str, items: list[_KnowledgeItem]) -> list[tuple[float, _KnowledgeItem]]:
    query_tokens = _tokenize(question)
    return sorted(
        ((_score_item(question, query_tokens, item), item) for item in items),
        key=lambda pair: pair[0],
        reverse=True,
    )


def _deterministic_support_answer(question: str, items: list[_KnowledgeItem]) -> SupportAnswer:
    normalized_question = (question or "").strip()

    if not normalized_question or not items:
        return SupportAnswer(
            answer=(
                "I can help with shipping, freshness, gifting, subscriptions, and other common Nest & Whisk questions. "
                "Try one of the suggested prompts below or visit our contact page for personal support."
            ),
            source_title="Support guidance",
            source_type="Assistant",
            follow_up_questions=_DEFAULT_FALLBACK_QUESTIONS,
            confidence=0.0,
        )

    ranked_items = _rank_knowledge_items(normalized_question, items)
    best_score, best_item = ranked_items[0]

    if best_score < 2.4:
        return SupportAnswer(
            answer=(
                "I couldn't find an exact answer in our bakery guide yet, but I can still point you in the right direction. "
                "Ask about freshness, gifting, delivery timing, subscriptions, allergens, or reach out for a tailored answer."
            ),
            source_title="Support guidance",
            source_type="Assistant",
            follow_up_questions=_DEFAULT_FALLBACK_QUESTIONS,
            confidence=best_score,
        )

    follow_ups = [
        pair[1].title
        for pair in ranked_items[1:4]
        if pair[1].title != best_item.title
    ]
    if not follow_ups:
        follow_ups = _DEFAULT_FALLBACK_QUESTIONS

    return SupportAnswer(
        answer=best_item.body,
        source_title=best_item.title,
        source_type=best_item.source_type,
        follow_up_questions=follow_ups,
        confidence=best_score,
        cta_url=best_item.url or "/contact/",
    )


def _build_ai_messages(*, question: str, fallback_answer: SupportAnswer, ranked_items: list[tuple[float, _KnowledgeItem]]) -> list[dict[str, str]]:
    context_blocks = []
    for score, item in ranked_items[:3]:
        context_blocks.append(
            f"Source type: {item.source_type}\n"
            f"Title: {item.title}\n"
            f"Category: {item.category}\n"
            f"URL: {item.url}\n"
            f"Relevance score: {score:.2f}\n"
            f"Content: {item.body}"
        )

    system_prompt = (
        "You are the Nest & Whisk support assistant for a premium artisan cookie store. "
        "Answer ONLY using the provided store knowledge. Keep answers warm, concise, and practical. "
        "If the knowledge does not fully answer the question, say so briefly and direct the customer to contact support. "
        "Do not invent policies, prices, timelines, or ingredients."
    )
    user_prompt = (
        f"Customer question: {question}\n\n"
        f"Fallback answer already verified from store content: {fallback_answer.answer}\n\n"
        f"Store knowledge:\n\n" + "\n\n---\n\n".join(context_blocks)
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def _request_openai_compatible_completion(*, messages: list[dict[str, str]]) -> str | None:
    if not settings.AI_CHAT_ENABLED or not settings.AI_CHAT_API_KEY:
        return None

    api_base = settings.AI_CHAT_BASE_URL.rstrip("/")
    payload = json.dumps(
        {
            "model": settings.AI_CHAT_MODEL,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 280,
        }
    ).encode("utf-8")
    req = request.Request(
        url=f"{api_base}/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.AI_CHAT_API_KEY}",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=settings.AI_CHAT_TIMEOUT_SECONDS) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        logger.warning("AI FAQ assistant request failed; falling back to deterministic answer: %s", exc)
        return None

    choices = data.get("choices") or []
    if not choices:
        return None
    message = choices[0].get("message") or {}
    content = (message.get("content") or "").strip()
    return content or None


def _request_gemini_completion(*, messages: list[dict[str, str]]) -> str | None:
    if not settings.AI_CHAT_ENABLED or not settings.AI_CHAT_API_KEY:
        return None

    api_base = settings.AI_CHAT_BASE_URL.rstrip("/")
    system_instruction = next((message["content"] for message in messages if message["role"] == "system"), "")
    user_parts = [
        {"text": message["content"]}
        for message in messages
        if message["role"] != "system"
    ]
    payload = json.dumps(
        {
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "contents": [{"role": "user", "parts": user_parts}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 280,
            },
        }
    ).encode("utf-8")
    req = request.Request(
        url=f"{api_base}/models/{settings.AI_CHAT_MODEL}:generateContent?key={settings.AI_CHAT_API_KEY}",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=settings.AI_CHAT_TIMEOUT_SECONDS) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        logger.warning("Gemini FAQ assistant request failed; falling back to deterministic answer: %s", exc)
        return None

    candidates = data.get("candidates") or []
    if not candidates:
        return None
    content = candidates[0].get("content") or {}
    parts = content.get("parts") or []
    text = "\n".join(part.get("text", "").strip() for part in parts if part.get("text"))
    return text.strip() or None


def _request_ai_completion(*, messages: list[dict[str, str]]) -> str | None:
    provider = (settings.AI_CHAT_PROVIDER or "").strip().lower()
    if provider == "gemini":
        return _request_gemini_completion(messages=messages)
    if provider in {"openai", "openai-compatible", ""}:
        return _request_openai_compatible_completion(messages=messages)

    logger.warning("Unsupported AI_CHAT_PROVIDER '%s'; falling back to deterministic FAQ assistant", provider)
    return None


def answer_support_question(question: str) -> SupportAnswer:
    normalized_question = (question or "").strip()
    items = _build_knowledge_items()
    fallback_answer = _deterministic_support_answer(normalized_question, items)
    ranked_items = _rank_knowledge_items(normalized_question, items) if normalized_question and items else []

    ai_text = _request_ai_completion(
        messages=_build_ai_messages(
            question=normalized_question,
            fallback_answer=fallback_answer,
            ranked_items=ranked_items,
        )
    )
    if not ai_text:
        return fallback_answer

    return SupportAnswer(
        answer=ai_text,
        source_title=fallback_answer.source_title,
        source_type="AI-assisted support",
        follow_up_questions=fallback_answer.follow_up_questions,
        confidence=fallback_answer.confidence,
        used_ai=True,
        model_name=settings.AI_CHAT_MODEL,
        cta_label=fallback_answer.cta_label,
        cta_url=fallback_answer.cta_url,
    )


