from django.contrib import admin

from apps.core.models import (
    ContactSettings,
    FAQ,
    HomepageContent,
    NewsletterSignup,
    PolicyPage,
    SiteSettings,
    Testimonial,
)

admin.site.site_header = "Nest & Whisk Admin"
admin.site.site_title = "Nest & Whisk Admin"
admin.site.index_title = "Boutique operations dashboard"


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        (
            "Brand",
            {"fields": ("site_name", "tag_line", "announcement_bar_text", "footer_blurb")},
        ),
        (
            "SEO",
            {"fields": ("meta_title", "meta_description")},
        ),
        (
            "Contact & social",
            {
                "fields": (
                    "support_email",
                    "support_phone",
                    "instagram_url",
                    "tiktok_url",
                    "pinterest_url",
                )
            },
        ),
    )

    def has_add_permission(self, request):
        if SiteSettings.objects.exists():
            return False
        return super().has_add_permission(request)


@admin.register(HomepageContent)
class HomepageContentAdmin(admin.ModelAdmin):
    fieldsets = (
        (
            "Hero",
            {
                "fields": (
                    "eyebrow",
                    "hero_title",
                    "hero_body",
                    "primary_cta_label",
                    "primary_cta_url",
                    "secondary_cta_label",
                    "secondary_cta_url",
                    "tertiary_cta_label",
                    "tertiary_cta_url",
                )
            },
        ),
        (
            "Feature cards",
            {
                "fields": (
                    "feature_one_label",
                    "feature_one_title",
                    "feature_one_body",
                    "feature_two_label",
                    "feature_two_title",
                    "feature_two_body",
                    "feature_banner_label",
                    "feature_banner_body",
                )
            },
        ),
        (
            "Quality section",
            {"fields": ("quality_title", "quality_body_left", "quality_body_right")},
        ),
    )

    def has_add_permission(self, request):
        if HomepageContent.objects.exists():
            return False
        return super().has_add_permission(request)


@admin.register(ContactSettings)
class ContactSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        (
            "Page content",
            {
                "fields": (
                    "page_title",
                    "intro",
                    "inquiry_email",
                    "business_hours",
                    "studio_location",
                    "contact_card_body",
                )
            },
        ),
    )

    def has_add_permission(self, request):
        if ContactSettings.objects.exists():
            return False
        return super().has_add_permission(request)


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ("question", "category", "is_published", "sort_order", "updated_at")
    list_filter = ("category", "is_published")
    search_fields = ("question", "answer")
    list_editable = ("sort_order", "is_published")


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ("customer_name", "customer_title", "rating", "is_featured", "sort_order")
    list_filter = ("is_featured", "rating")
    search_fields = ("customer_name", "customer_title", "quote")
    list_editable = ("rating", "is_featured", "sort_order")


@admin.register(PolicyPage)
class PolicyPageAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "is_published", "sort_order", "updated_at")
    list_filter = ("is_published",)
    search_fields = ("title", "summary", "body")
    prepopulated_fields = {"slug": ("title",)}
    list_editable = ("is_published", "sort_order")


@admin.register(NewsletterSignup)
class NewsletterSignupAdmin(admin.ModelAdmin):
    list_display = ("email", "first_name", "source", "is_active", "created_at")
    list_filter = ("source", "is_active", "confirmed_at")
    search_fields = ("email", "first_name")
    readonly_fields = ("created_at", "updated_at", "confirmed_at")

