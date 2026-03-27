from django import forms

from apps.accounts.forms import FORM_INPUT_CLASS
from apps.corporate.models import CorporateInquiry


class CorporateInquiryForm(forms.ModelForm):
    class Meta:
        model = CorporateInquiry
        fields = [
            "company_name",
            "contact_name",
            "email",
            "phone_number",
            "occasion",
            "quantity_estimate",
            "budget_range",
            "event_date",
            "delivery_date",
            "gifting_goal",
            "notes",
        ]
        widgets = {
            "event_date": forms.DateInput(attrs={"type": "date"}),
            "delivery_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", FORM_INPUT_CLASS)

