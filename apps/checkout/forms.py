from django import forms

from apps.accounts.forms import FORM_INPUT_CLASS


class CheckoutForm(forms.Form):
    PAYMENT_PROVIDER_STRIPE = "stripe"
    PAYMENT_PROVIDER_MOCK = "mock"

    PAYMENT_PREFERENCE_CARD = "card"
    PAYMENT_PREFERENCE_UPI = "upi"
    PAYMENT_PREFERENCE_FLEXIBLE = "flexible"

    PAYMENT_PREFERENCE_CHOICES = [
        (PAYMENT_PREFERENCE_CARD, "Card"),
        (PAYMENT_PREFERENCE_UPI, "UPI"),
        (PAYMENT_PREFERENCE_FLEXIBLE, "Best available option"),
    ]

    PAYMENT_PROVIDER_CHOICES = [
        (PAYMENT_PROVIDER_STRIPE, "Stripe test mode"),
        (PAYMENT_PROVIDER_MOCK, "Mock payment simulator"),
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
    payment_provider = forms.ChoiceField(
        choices=PAYMENT_PROVIDER_CHOICES,
        initial=PAYMENT_PROVIDER_STRIPE,
        widget=forms.RadioSelect,
    )
    payment_preference = forms.ChoiceField(
        choices=PAYMENT_PREFERENCE_CHOICES,
        initial=PAYMENT_PREFERENCE_FLEXIBLE,
        widget=forms.RadioSelect,
    )

    def __init__(self, *args, **kwargs):
        allow_upi = kwargs.pop("allow_upi", False)
        allow_mock = kwargs.pop("allow_mock", False)
        default_payment_provider = kwargs.pop("default_payment_provider", self.PAYMENT_PROVIDER_STRIPE)
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", FORM_INPUT_CLASS)
        provider_choices = [(self.PAYMENT_PROVIDER_STRIPE, "Stripe test mode")]
        if allow_mock:
            provider_choices.append((self.PAYMENT_PROVIDER_MOCK, "Mock payment simulator"))
        self.fields["payment_provider"].choices = provider_choices
        self.fields["payment_provider"].initial = default_payment_provider if default_payment_provider in {value for value, _label in provider_choices} else self.PAYMENT_PROVIDER_STRIPE
        self.fields["payment_provider"].widget.attrs.pop("class", None)
        payment_choices = [
            (self.PAYMENT_PREFERENCE_CARD, "Card"),
            (self.PAYMENT_PREFERENCE_FLEXIBLE, "Best available option"),
        ]
        if allow_upi:
            payment_choices.insert(1, (self.PAYMENT_PREFERENCE_UPI, "UPI"))
        self.fields["payment_preference"].choices = payment_choices
        self.fields["payment_preference"].widget.attrs.pop("class", None)
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
