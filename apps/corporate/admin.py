from django.contrib import admin

from apps.corporate.models import CorporateInquiry, CorporatePageContent


@admin.register(CorporatePageContent)
class CorporatePageContentAdmin(admin.ModelAdmin):
    fieldsets = (
        (
            "Hero",
            {"fields": ("eyebrow", "title", "intro")},
        ),
        (
            "Editorial cards",
            {
                "fields": (
                    "capability_title",
                    "capability_body",
                    "lead_time_title",
                    "lead_time_body",
                    "consultation_title",
                    "consultation_body",
                )
            },
        ),
    )

    def has_add_permission(self, request):
        if CorporatePageContent.objects.exists():
            return False
        return super().has_add_permission(request)


@admin.register(CorporateInquiry)
class CorporateInquiryAdmin(admin.ModelAdmin):
    list_display = (
        "company_name",
        "contact_name",
        "email",
        "quantity_estimate",
        "budget_range",
        "status",
        "delivery_date",
    )
    list_filter = ("status", "budget_range", "source", "campaign")
    search_fields = ("company_name", "contact_name", "email", "phone_number")
    readonly_fields = ("created_at", "updated_at")

