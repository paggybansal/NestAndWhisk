from django.contrib import admin

from apps.catalog.models import (
    DietaryAttribute,
    Product,
    ProductCategory,
    ProductImage,
    ProductTag,
    ProductVariant,
)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ("image", "video_file", "alt_text", "is_primary", "sort_order")


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = (
        "name",
        "sku",
        "pack_size",
        "price",
        "compare_at_price",
        "inventory_quantity",
        "low_stock_threshold",
        "is_default",
        "is_active",
        "sort_order",
    )


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "sort_order", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "description", "short_description")
    list_editable = ("is_active", "sort_order")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(ProductTag)
class ProductTagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(DietaryAttribute)
class DietaryAttributeAdmin(admin.ModelAdmin):
    list_display = ("name", "badge_label", "slug")
    search_fields = ("name", "badge_label")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "is_active",
        "is_featured",
        "is_seasonal",
        "sort_order",
    )
    list_filter = (
        "category",
        "is_active",
        "is_featured",
        "is_seasonal",
    )
    search_fields = (
        "name",
        "short_description",
        "description",
        "ingredients",
        "ingredient_highlights",
        "pairing_notes",
        "video_caption",
    )
    list_editable = ("is_active", "is_featured", "is_seasonal", "sort_order")
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ("tags", "dietary_attributes")
    inlines = [ProductImageInline, ProductVariantInline]
    fieldsets = (
        (
            "Core product details",
            {
                "fields": (
                    "category",
                    "name",
                    "slug",
                    "short_description",
                    "description",
                    "featured_label",
                    "is_active",
                    "is_featured",
                    "is_seasonal",
                    "sort_order",
                )
            },
        ),
        (
            "Product details & dietary notes",
            {
                "fields": (
                    "ingredients",
                    "ingredient_highlights",
                    "allergen_information",
                    "nutritional_notes",
                    "care_instructions",
                    "storage_guidance",
                    "shelf_life_days",
                )
            },
        ),
        (
            "Merchandising extras",
            {
                "fields": (
                    ("texture_chewy", "texture_crunchy", "texture_gooey"),
                    "pairing_notes",
                    "video_caption",
                    "tags",
                    "dietary_attributes",
                )
            },
        ),
        (
            "SEO",
            {
                "classes": ("collapse",),
                "fields": ("meta_title", "meta_description"),
            },
        ),
    )


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "name",
        "sku",
        "pack_size",
        "price",
        "inventory_quantity",
        "is_active",
        "is_default",
    )
    list_filter = ("is_active", "is_default", "product__category")
    search_fields = ("product__name", "name", "sku")
    list_editable = ("price", "inventory_quantity", "is_active", "is_default")


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("product", "is_primary", "sort_order")
    list_filter = ("is_primary",)
    search_fields = ("product__name", "alt_text")
    fields = ("product", "image", "video_file", "alt_text", "is_primary", "sort_order")
    list_editable = ("is_primary", "sort_order")
