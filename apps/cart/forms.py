from django import forms

from apps.accounts.forms import FORM_INPUT_CLASS


class AddToCartForm(forms.Form):
    variant_id = forms.IntegerField(required=False, widget=forms.HiddenInput())
    quantity = forms.IntegerField(min_value=1, initial=1)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if not isinstance(field.widget, forms.HiddenInput):
                field.widget.attrs["class"] = FORM_INPUT_CLASS


class CartItemUpdateForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, widget=forms.NumberInput(attrs={"class": FORM_INPUT_CLASS}))
