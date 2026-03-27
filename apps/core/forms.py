from django import forms

from apps.core.models import NewsletterSignup


class FAQAssistantForm(forms.Form):
    question = forms.CharField(
        max_length=240,
        strip=True,
        widget=forms.TextInput(
            attrs={
                "id": "faq-assistant-question",
                "placeholder": "Ask about products, flavors, shipping, gifting, or subscriptions…",
                "class": "w-full rounded-full border border-cocoa/15 bg-white px-5 py-3 text-sm text-cocoa placeholder:text-cocoa/45 focus:border-caramel focus:outline-none focus:ring-0",
            }
        ),
    )

    def clean_question(self):
        question = self.cleaned_data["question"].strip()
        if len(question) < 3:
            raise forms.ValidationError("Please enter a fuller question so I can help.")
        return question


class NewsletterSignupForm(forms.ModelForm):
    class Meta:
        model = NewsletterSignup
        fields = ["first_name", "email"]
        widgets = {
            "first_name": forms.TextInput(
                attrs={
                    "placeholder": "First name",
                    "class": "w-full rounded-full border border-cocoa/15 bg-white px-5 py-3 text-sm text-cocoa placeholder:text-cocoa/45 focus:border-caramel focus:outline-none focus:ring-0",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "placeholder": "Email address",
                    "class": "w-full rounded-full border border-cocoa/15 bg-white px-5 py-3 text-sm text-cocoa placeholder:text-cocoa/45 focus:border-caramel focus:outline-none focus:ring-0",
                }
            ),
        }

    def save(self, commit: bool = True):
        cleaned_email = self.cleaned_data["email"]
        defaults = {
            "first_name": self.cleaned_data.get("first_name", ""),
            "source": "homepage",
            "is_active": True,
        }
        instance, _created = NewsletterSignup.objects.update_or_create(
            email=cleaned_email,
            defaults=defaults,
        )
        return instance
