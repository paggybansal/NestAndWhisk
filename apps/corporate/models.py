from django.conf import settings
from django.db import models

from apps.core.models import SingletonModel, TimeStampedModel
from apps.marketing.models import CampaignAttribution, MarketingSource


class CorporatePageContent(SingletonModel):
    eyebrow = models.CharField(max_length=120, default="Corporate gifting")
    title = models.CharField(
        max_length=180,
        default="Premium cookie gifting for clients, teams, and memorable moments.",
    )
    intro = models.TextField(
        default=(
            "From elevated client gifts to polished team celebrations, Nest & Whisk creates artisan cookie experiences that feel thoughtful, giftable, and unmistakably premium."
        )
    )
    capability_title = models.CharField(max_length=120, default="What we can tailor")
    capability_body = models.TextField(
        default=(
            "Curated assortments, seasonal gifting, branded notes, premium packaging, and delivery timing planned around launches, campaigns, and events."
        )
    )
    lead_time_title = models.CharField(max_length=120, default="Typical lead time")
    lead_time_body = models.TextField(
        default=(
            "Most gifting briefs can be reviewed within one to two business days, with custom event timelines and higher-volume requests handled case by case."
        )
    )
    consultation_title = models.CharField(max_length=120, default="Why brands choose us")
    consultation_body = models.TextField(
        default=(
            "Our team blends hospitality-minded service with boutique presentation, so every gifting touchpoint feels polished from the first inquiry to final delivery."
        )
    )

    class Meta:
        verbose_name = "corporate page content"
        verbose_name_plural = "corporate page content"

    def __str__(self) -> str:
        return "Corporate page content"


class CorporateInquiry(TimeStampedModel):
    class BudgetRange(models.TextChoices):
        UNDER_250 = "under_250", "Under ₹20,000"
        BETWEEN_250_500 = "250_500", "₹20,000 - ₹40,000"
        BETWEEN_500_1000 = "500_1000", "₹40,000 - ₹80,000"
        OVER_1000 = "over_1000", "Over ₹80,000"

    class Status(models.TextChoices):
        NEW = "new", "New"
        IN_REVIEW = "in_review", "In review"
        QUOTED = "quoted", "Quoted"
        WON = "won", "Won"
        CLOSED = "closed", "Closed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="corporate_inquiries",
    )
    source = models.ForeignKey(
        MarketingSource,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="corporate_inquiries",
    )
    campaign = models.ForeignKey(
        CampaignAttribution,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="corporate_inquiries",
    )
    company_name = models.CharField(max_length=180)
    contact_name = models.CharField(max_length=160)
    email = models.EmailField()
    phone_number = models.CharField(max_length=32, blank=True)
    occasion = models.CharField(max_length=120, blank=True)
    quantity_estimate = models.PositiveIntegerField(default=1)
    budget_range = models.CharField(max_length=20, choices=BudgetRange.choices)
    event_date = models.DateField(null=True, blank=True)
    delivery_date = models.DateField(null=True, blank=True)
    gifting_goal = models.CharField(max_length=160, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    admin_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "delivery_date"])]

    def __str__(self) -> str:
        return f"{self.company_name} · {self.contact_name}"
