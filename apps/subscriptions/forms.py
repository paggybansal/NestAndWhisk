from django import forms

from apps.accounts.forms import FORM_INPUT_CLASS
from apps.subscriptions.models import SubscriptionPlan, UserSubscription


class SubscriptionSignupForm(forms.Form):
    plan = forms.ModelChoiceField(queryset=SubscriptionPlan.objects.filter(is_active=True))
    flavor_preferences = forms.CharField(
        required=False,
        help_text="Separate flavor notes with commas.",
    )
    renewal_day = forms.IntegerField(min_value=1, max_value=28, initial=1)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", FORM_INPUT_CLASS)


class SubscriptionPreferencesForm(forms.ModelForm):
    flavor_preferences_text = forms.CharField(required=False)

    class Meta:
        model = UserSubscription
        fields = ["renewal_day"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["flavor_preferences_text"].initial = ", ".join(self.instance.flavor_preferences or [])
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", FORM_INPUT_CLASS)

    def save(self, commit=True):
        instance = super().save(commit=False)
        preferences = self.cleaned_data.get("flavor_preferences_text", "")
        instance.flavor_preferences = [item.strip() for item in preferences.split(",") if item.strip()]
        if commit:
            instance.save()
        return instance


class SubscriptionStatusForm(forms.Form):
    subscription_id = forms.IntegerField(widget=forms.HiddenInput())

