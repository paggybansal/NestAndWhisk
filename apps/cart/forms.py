from django import forms

from apps.accounts.forms import FORM_INPUT_CLASS
from apps.catalog.models import Product, ProductVariant


BUILD_A_BOX_CATEGORY_SLUG = "build-a-box"


class AddToCartForm(forms.Form):
    variant_id = forms.IntegerField(required=False, widget=forms.HiddenInput())
    quantity = forms.IntegerField(min_value=1, initial=1)
    gift_message = forms.CharField(required=False, max_length=255)
    packaging_option = forms.CharField(required=False, max_length=80)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if not isinstance(field.widget, forms.HiddenInput):
                field.widget.attrs["class"] = FORM_INPUT_CLASS
                if name == "gift_message":
                    field.widget.attrs["placeholder"] = "Gift message (optional)"
                if name == "packaging_option":
                    field.widget.attrs["placeholder"] = "Packaging preference"


class CartItemUpdateForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, widget=forms.NumberInput(attrs={"class": FORM_INPUT_CLASS}))


class BuildABoxForm(forms.Form):
    base_product = forms.ModelChoiceField(
        queryset=Product.objects.filter(
            is_active=True,
            allows_build_a_box=True,
            category__slug=BUILD_A_BOX_CATEGORY_SLUG,
        ),
        empty_label=None,
    )
    variant = forms.ModelChoiceField(
        queryset=ProductVariant.objects.filter(
            is_active=True,
            inventory_quantity__gt=0,
            product__category__slug=BUILD_A_BOX_CATEGORY_SLUG,
        ).select_related("product"),
        empty_label=None,
    )
    quantity = forms.IntegerField(min_value=1, initial=1)
    flavors = forms.ModelMultipleChoiceField(
        queryset=Product.objects.filter(is_active=True, allows_build_a_box=True).exclude(
            category__slug=BUILD_A_BOX_CATEGORY_SLUG,
        ),
        widget=forms.CheckboxSelectMultiple,
    )
    gift_message = forms.CharField(required=False, max_length=255)
    packaging_option = forms.CharField(required=False, max_length=80)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["gift_message"].widget.attrs.update({"placeholder": "Gift message (optional)", "class": FORM_INPUT_CLASS})
        self.fields["packaging_option"].widget.attrs.update({"placeholder": "Packaging preference", "class": FORM_INPUT_CLASS})
        self.fields["quantity"].widget.attrs.update({"class": FORM_INPUT_CLASS})
        self.fields["base_product"].widget.attrs.update({"class": FORM_INPUT_CLASS})
        self.fields["variant"].widget.attrs.update({"class": FORM_INPUT_CLASS})

    def clean(self):
        cleaned_data = super().clean()
        variant = cleaned_data.get("variant")
        flavors = cleaned_data.get("flavors")
        if variant and flavors and len(flavors) != variant.pack_size:
            self.add_error("flavors", f"Please choose exactly {variant.pack_size} cookies for this box size.")
        if variant and cleaned_data.get("base_product") and variant.product_id != cleaned_data["base_product"].id:
            self.add_error("variant", "Please choose a box size for the selected build-a-box product.")
        return cleaned_data
