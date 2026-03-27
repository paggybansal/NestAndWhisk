from allauth.account.forms import LoginForm, ResetPasswordForm, SignupForm
from django import forms

from apps.accounts.models import User


FORM_INPUT_CLASS = (
    "w-full rounded-2xl border border-cocoa/15 bg-white px-4 py-3 text-sm text-cocoa "
    "placeholder:text-cocoa/45 focus:border-caramel focus:outline-none focus:ring-0"
)
CHECKBOX_CLASS = "h-4 w-4 rounded border-cocoa/20 text-caramel focus:ring-caramel"


class StyledFormMixin:
    def apply_styling(self):
        for name, field in self.fields.items():
            widget = field.widget
            existing_class = widget.attrs.get("class", "")
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = f"{existing_class} {CHECKBOX_CLASS}".strip()
            else:
                widget.attrs["class"] = f"{existing_class} {FORM_INPUT_CLASS}".strip()


class CustomerLoginForm(StyledFormMixin, LoginForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["login"].label = "Email address"
        self.fields["login"].widget.attrs.update({"placeholder": "you@example.com"})
        self.fields["password"].widget.attrs.update({"placeholder": "Enter your password"})
        self.apply_styling()


class CustomerSignupForm(StyledFormMixin, SignupForm):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=False)
    marketing_opt_in = forms.BooleanField(required=False, initial=True)

    field_order = ["first_name", "last_name", "email", "password1", "password2", "marketing_opt_in"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].widget.attrs.update({"placeholder": "First name"})
        self.fields["last_name"].widget.attrs.update({"placeholder": "Last name"})
        self.fields["email"].widget.attrs.update({"placeholder": "you@example.com"})
        self.fields["password1"].widget.attrs.update({"placeholder": "Create a password"})
        self.fields["password2"].widget.attrs.update({"placeholder": "Confirm your password"})
        self.fields["marketing_opt_in"].label = "Email me seasonal launches, gifting moments, and bakery updates."
        self.apply_styling()

    def save(self, request):
        user = super().save(request)
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data.get("last_name", "")
        user.marketing_opt_in = self.cleaned_data.get("marketing_opt_in", False)
        user.save(update_fields=["first_name", "last_name", "marketing_opt_in"])
        return user


class CustomerResetPasswordForm(StyledFormMixin, ResetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].widget.attrs.update({"placeholder": "you@example.com"})
        self.apply_styling()


class CustomerProfileForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "phone_number", "marketing_opt_in"]
        widgets = {
            "first_name": forms.TextInput(attrs={"placeholder": "First name"}),
            "last_name": forms.TextInput(attrs={"placeholder": "Last name"}),
            "email": forms.EmailInput(attrs={"placeholder": "you@example.com"}),
            "phone_number": forms.TextInput(attrs={"placeholder": "+1 (555) 123-4567"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["marketing_opt_in"].label = "Keep me in the loop about seasonal boxes, launches, and gifting updates."
        self.apply_styling()
