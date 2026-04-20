from django import forms

from apps.accounts.forms import FORM_INPUT_CLASS
from apps.core.delivery import get_delhi_ncr_delivery_experience, normalize_postal_code


class CheckoutForm(forms.Form):
    PAYMENT_OPTION_COD = "cod"  # kept for backward compatibility with existing order data only
    PAYMENT_OPTION_ONLINE_LINK = "online_link"

    PAYMENT_OPTION_CHOICES = [
        (PAYMENT_OPTION_ONLINE_LINK, "Pay Online (payment link via team)"),
    ]

    customer_email = forms.EmailField()
    customer_first_name = forms.CharField(max_length=120)
    customer_last_name = forms.CharField(max_length=120, required=False)
    customer_phone = forms.CharField(max_length=32, required=False)
    shipping_address_line_1 = forms.CharField(max_length=255)
    shipping_address_line_2 = forms.CharField(max_length=255, required=False)
    shipping_city = forms.CharField(max_length=120)
    shipping_state = forms.CharField(max_length=120)
    shipping_postal_code = forms.CharField(max_length=20)
    shipping_country = forms.CharField(max_length=120, initial="India")
    delivery_notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 4}))
    payment_option = forms.ChoiceField(
        choices=PAYMENT_OPTION_CHOICES,
        initial=PAYMENT_OPTION_ONLINE_LINK,
        widget=forms.RadioSelect,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", FORM_INPUT_CLASS)
        self.fields["payment_option"].widget.attrs.pop("class", None)
        self.fields["customer_email"].widget.attrs.update(
            {
                "placeholder": "you@example.com",
                "autocomplete": "email",
            }
        )
        self.fields["customer_first_name"].widget.attrs.update(
            {
                "placeholder": "First name",
                "autocomplete": "given-name",
            }
        )
        self.fields["customer_last_name"].widget.attrs.update(
            {
                "placeholder": "Last name",
                "autocomplete": "family-name",
            }
        )
        self.fields["customer_phone"].widget.attrs.update(
            {
                "placeholder": "98765 43210",
                "autocomplete": "tel",
            }
        )
        self.fields["shipping_address_line_1"].widget.attrs.update(
            {
                "placeholder": "House number, street, or building",
                "autocomplete": "address-line1",
            }
        )
        self.fields["shipping_address_line_2"].widget.attrs.update(
            {
                "placeholder": "Apartment, suite, landmark, or floor",
                "autocomplete": "address-line2",
            }
        )
        self.fields["shipping_city"].widget.attrs.update(
            {
                "placeholder": "Delhi, Gurugram, Noida…",
                "autocomplete": "address-level2",
            }
        )
        self.fields["shipping_state"].widget.attrs.update(
            {
                "placeholder": "Delhi / Haryana / Uttar Pradesh",
                "autocomplete": "address-level1",
            }
        )
        self.fields["shipping_postal_code"].widget.attrs.update(
            {
                "placeholder": "110001",
                "inputmode": "numeric",
                "autocomplete": "postal-code",
            }
        )
        self.fields["shipping_country"].widget.attrs.update({"autocomplete": "country-name"})
        self.fields["delivery_notes"].widget.attrs.setdefault(
            "placeholder",
            "Gate code, landmark, preferred slot, or gifting instructions",
        )

    def clean_shipping_postal_code(self):
        raw_postal_code = self.cleaned_data.get("shipping_postal_code", "")
        normalized_postal_code = normalize_postal_code(raw_postal_code)
        experience = get_delhi_ncr_delivery_experience(
            city=self.cleaned_data.get("shipping_city", ""),
            postal_code=normalized_postal_code,
        )
        if not experience.get("is_express_zone"):
            raise forms.ValidationError("We currently deliver only in Delhi NCR. Please enter a valid Delhi NCR pincode.")
        return normalized_postal_code


class OrderLookupForm(forms.Form):
    order_number = forms.CharField(max_length=20)
    customer_email = forms.EmailField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["order_number"].widget.attrs.update({
            "class": FORM_INPUT_CLASS,
            "placeholder": "Order number (for example NW1234ABCD)",
        })
        self.fields["customer_email"].widget.attrs.update({
            "class": FORM_INPUT_CLASS,
            "placeholder": "Email used at checkout",
        })


class TrackingLinkRequestForm(forms.Form):
    customer_email = forms.EmailField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["customer_email"].widget.attrs.update({
            "class": FORM_INPUT_CLASS,
            "placeholder": "Email used at checkout",
        })
