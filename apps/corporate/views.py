from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import FormView

from apps.core.views import CoreContextMixin
from apps.corporate.forms import CorporateInquiryForm
from apps.corporate.models import CorporatePageContent
from apps.marketing.models import CampaignAttribution, MarketingSource


class CorporateInquiryView(CoreContextMixin, FormView):
    template_name = "corporate/inquiry.html"
    form_class = CorporateInquiryForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_content"] = CorporatePageContent.load()
        return context

    def form_valid(self, form):
        inquiry = form.save(commit=False)
        if self.request.user.is_authenticated:
            inquiry.user = self.request.user

        source_slug = self.request.GET.get("source") or self.request.POST.get("source")
        campaign_code = self.request.GET.get("campaign") or self.request.POST.get("campaign")

        if source_slug:
            inquiry.source = MarketingSource.objects.filter(slug=source_slug, is_active=True).first()
        if campaign_code:
            inquiry.campaign = CampaignAttribution.objects.filter(campaign_code=campaign_code, is_active=True).first()

        inquiry.save()
        messages.success(
            self.request,
            "Thanks for reaching out. Our gifting team will review your brief and reply with next steps soon.",
        )
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse("corporate:inquiry")

