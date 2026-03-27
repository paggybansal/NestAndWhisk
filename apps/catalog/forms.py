from django import forms

from apps.accounts.forms import FORM_INPUT_CLASS
from apps.catalog.models import DietaryAttribute, ProductCategory


SORT_CHOICES = [
    ("featured", "Featured"),
    ("newest", "Newest"),
    ("price_asc", "Price: Low to High"),
    ("price_desc", "Price: High to Low"),
    ("name", "Name"),
]


class CatalogFilterForm(forms.Form):
    search = forms.CharField(required=False)
    category = forms.ModelChoiceField(
        queryset=ProductCategory.objects.filter(is_active=True),
        required=False,
        empty_label="All categories",
        to_field_name="slug",
    )
    dietary = forms.ModelChoiceField(
        queryset=DietaryAttribute.objects.all(),
        required=False,
        empty_label="All dietary needs",
    )
    in_stock = forms.BooleanField(required=False)
    sort = forms.ChoiceField(choices=SORT_CHOICES, required=False, initial="featured")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "h-4 w-4 rounded border-cocoa/20 text-caramel focus:ring-caramel"
            else:
                field.widget.attrs["class"] = FORM_INPUT_CLASS
        self.fields["search"].widget.attrs.update(
            {
                "placeholder": "Search signature flavours, gifting boxes, or textures",
                "aria-label": "Search products",
            }
        )
        self.fields["category"].widget.attrs.update({"aria-label": "Filter by category"})
        self.fields["dietary"].widget.attrs.update({"aria-label": "Filter by dietary preference"})
        self.fields["sort"].widget.attrs.update({"aria-label": "Sort products"})

