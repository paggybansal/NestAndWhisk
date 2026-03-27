from django.contrib import admin

from apps.marketing.models import CampaignAttribution, MarketingSource


@admin.register(MarketingSource)
class MarketingSourceAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "channel", "is_active")
    search_fields = ("name", "slug", "channel")
    list_filter = ("is_active", "channel")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(CampaignAttribution)
class CampaignAttributionAdmin(admin.ModelAdmin):
    list_display = ("campaign_name", "campaign_code", "source", "medium", "is_active")
    search_fields = ("campaign_name", "campaign_code", "content_label")
    list_filter = ("is_active", "source", "medium")

