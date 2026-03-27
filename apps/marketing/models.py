from django.db import models

from apps.core.models import TimeStampedModel


class MarketingSource(TimeStampedModel):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True)
    channel = models.CharField(max_length=80, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class CampaignAttribution(TimeStampedModel):
    source = models.ForeignKey(
        MarketingSource,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="campaigns",
    )
    campaign_name = models.CharField(max_length=120)
    campaign_code = models.CharField(max_length=80, blank=True)
    medium = models.CharField(max_length=80, blank=True)
    content_label = models.CharField(max_length=120, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["campaign_name"]
        indexes = [models.Index(fields=["campaign_name", "campaign_code"])]

    def __str__(self) -> str:
        return self.campaign_name
