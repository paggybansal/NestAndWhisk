from django import forms

from apps.accounts.forms import FORM_INPUT_CLASS
from apps.reviews.models import Review


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["customer_name", "customer_email", "rating", "title", "body"]
        widgets = {
            "customer_name": forms.TextInput(attrs={"placeholder": "Your name"}),
            "customer_email": forms.EmailInput(attrs={"placeholder": "you@example.com"}),
            "rating": forms.Select(),
            "title": forms.TextInput(attrs={"placeholder": "A quick headline for your review"}),
            "body": forms.Textarea(attrs={"rows": 5, "placeholder": "Tell us what made this cookie box memorable."}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = FORM_INPUT_CLASS

