from decimal import Decimal
import re
from urllib.parse import urlparse

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from apps.core.models import TimeStampedModel

_LIST_SPLIT_RE = re.compile(r"[,;\n]+")


def _split_list_field(value: str, *, max_items: int = 4) -> list[str]:
    items = [item.strip(" •-\t") for item in _LIST_SPLIT_RE.split(value or "") if item.strip()]
    return items[:max_items]


def _clamp_texture_score(value: int) -> int:
    return max(1, min(5, value))


class ProductCategory(TimeStampedModel):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField(blank=True)
    short_description = models.CharField(max_length=220, blank=True)
    image = models.ImageField(upload_to="catalog/categories/", blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    seo_title = models.CharField(max_length=160, blank=True)
    seo_description = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "product category"
        verbose_name_plural = "product categories"

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("catalog:shop") + f"?category={self.slug}"


class ProductTag(TimeStampedModel):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "product tag"
        verbose_name_plural = "product tags"

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class DietaryAttribute(TimeStampedModel):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    badge_label = models.CharField(max_length=40, blank=True)
    description = models.CharField(max_length=220, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "dietary attribute"
        verbose_name_plural = "dietary attributes"

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        if not self.badge_label:
            self.badge_label = self.name
        super().save(*args, **kwargs)


class Product(TimeStampedModel):
    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.PROTECT,
        related_name="products",
    )
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True)
    short_description = models.CharField(max_length=240)
    description = models.TextField()
    ingredients = models.TextField(blank=True)
    ingredient_highlights = models.CharField(max_length=255, blank=True)
    allergen_information = models.TextField(blank=True)
    nutritional_notes = models.TextField(blank=True)
    care_instructions = models.CharField(max_length=220, blank=True)
    texture_chewy = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
    )
    texture_crunchy = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
    )
    texture_gooey = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
    )
    pairing_notes = models.CharField(max_length=255, blank=True)
    shelf_life_days = models.PositiveSmallIntegerField(null=True, blank=True)
    storage_guidance = models.CharField(max_length=255, blank=True)
    video_file = models.FileField(upload_to="catalog/videos/", blank=True)
    video_url = models.URLField(max_length=500, blank=True)
    video_caption = models.CharField(max_length=160, blank=True)
    featured_label = models.CharField(max_length=60, blank=True)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_seasonal = models.BooleanField(default=False)
    sort_order = models.PositiveSmallIntegerField(default=0)
    meta_title = models.CharField(max_length=160, blank=True)
    meta_description = models.CharField(max_length=255, blank=True)
    tags = models.ManyToManyField(ProductTag, related_name="products", blank=True)
    dietary_attributes = models.ManyToManyField(
        DietaryAttribute,
        related_name="products",
        blank=True,
    )

    class Meta:
        ordering = ["sort_order", "name"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["is_active", "is_featured"]),
            models.Index(fields=["category", "is_active"]),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("catalog:product_detail", kwargs={"slug": self.slug})

    @property
    def primary_image(self):
        return self.images.filter(is_primary=True).exclude(image="").first() or self.images.exclude(image="").order_by("sort_order", "id").first()

    @property
    def primary_stack_video(self):
        return self.images.exclude(video_file="").order_by("sort_order", "id").first()

    @property
    def default_variant(self):
        return self.variants.filter(is_active=True).order_by("sort_order", "price", "id").first()

    @property
    def price_from(self):
        variant = self.default_variant
        return variant.price if variant else Decimal("0.00")

    @property
    def is_in_stock(self) -> bool:
        return self.variants.filter(is_active=True, inventory_quantity__gt=0).exists()

    @property
    def ingredient_highlight_items(self) -> list[str]:
        explicit_items = _split_list_field(self.ingredient_highlights)
        if explicit_items:
            return explicit_items
        return _split_list_field(self.ingredients)

    def _inferred_texture_scores(self) -> dict[str, int]:
        haystack = f"{self.name} {self.short_description} {self.description} {self.ingredients}".lower()
        chewy = 2
        crunchy = 1
        gooey = 2

        chewy_keywords = ("chewy", "soft baked", "soft-baked", "buttery", "caramel", "brown butter", "oat")
        crunchy_keywords = ("crunchy", "crisp", "shortbread", "wafer", "biscotti", "toasted", "nutty crunch")
        gooey_keywords = ("gooey", "molten", "fudgy", "fudge", "ganache", "melt", "chocolate", "lava")

        chewy += sum(keyword in haystack for keyword in chewy_keywords)
        crunchy += sum(keyword in haystack for keyword in crunchy_keywords)
        gooey += sum(keyword in haystack for keyword in gooey_keywords)

        return {
            "Chewy": _clamp_texture_score(chewy),
            "Crunchy": _clamp_texture_score(crunchy),
            "Gooey": _clamp_texture_score(gooey),
        }

    @property
    def texture_meter_items(self) -> list[dict[str, int | str]]:
        inferred_scores = self._inferred_texture_scores()
        texture_map = {
            "Chewy": self.texture_chewy or inferred_scores["Chewy"],
            "Crunchy": self.texture_crunchy or inferred_scores["Crunchy"],
            "Gooey": self.texture_gooey or inferred_scores["Gooey"],
        }
        return [
            {
                "label": label,
                "score": score,
                "percentage": int((score / 5) * 100),
            }
            for label, score in texture_map.items()
        ]

    @property
    def pairing_items(self) -> list[dict[str, str]]:
        pairing_notes = {
            "coffee": "A rich espresso, cappuccino, or pour-over sharpens the cookie’s buttery depth.",
            "tea": "Masala chai, Earl Grey, or a classic black tea keeps the finish warm and balanced.",
            "milk": "Cold milk softens the sweetness and makes every bite feel extra bakery-fresh.",
        }
        explicit_items = _split_list_field(self.pairing_notes, max_items=3)
        if explicit_items:
            items: list[dict[str, str]] = []
            for item in explicit_items:
                normalized = item.lower()
                if "coffee" in normalized or "espresso" in normalized:
                    label = "Coffee"
                    note = pairing_notes["coffee"]
                elif "tea" in normalized or "chai" in normalized:
                    label = "Tea"
                    note = pairing_notes["tea"]
                elif "milk" in normalized:
                    label = "Milk"
                    note = pairing_notes["milk"]
                else:
                    label = item.title()
                    note = "A thoughtful pairing that rounds out the cookie’s flavor profile beautifully."
                items.append({"label": label, "note": note})
            return items

        haystack = f"{self.name} {self.short_description} {self.description} {self.ingredients}".lower()
        inferred_keys: list[str] = []
        if any(keyword in haystack for keyword in ("chocolate", "espresso", "caramel", "hazelnut")):
            inferred_keys.append("coffee")
        if any(keyword in haystack for keyword in ("chai", "tea", "cardamom", "cinnamon", "ginger", "rose")):
            inferred_keys.append("tea")
        if any(keyword in haystack for keyword in ("vanilla", "cookie", "brown sugar", "sea salt", "milk chocolate", "butter")):
            inferred_keys.append("milk")
        if not inferred_keys:
            inferred_keys = ["coffee", "tea", "milk"]

        return [
            {"label": key.title(), "note": pairing_notes[key]}
            for key in dict.fromkeys(inferred_keys)
        ][:3]

    @property
    def shelf_life_display(self) -> str:
        if self.shelf_life_days:
            if self.shelf_life_days == 1:
                return "Best enjoyed within 1 day of delivery for the softest texture."
            return f"Best enjoyed within {self.shelf_life_days} days of delivery for peak texture and flavor."
        if self.care_instructions:
            return self.care_instructions
        return "Best enjoyed within 5 to 7 days when stored with care after delivery."

    @property
    def storage_guidance_display(self) -> str:
        if self.storage_guidance:
            return self.storage_guidance
        if self.care_instructions:
            return self.care_instructions
        return "Store in an airtight container in a cool, dry spot. Warm briefly before serving for a bakery-fresh bite."

    @property
    def serving_tip_display(self) -> str:
        if self.nutritional_notes:
            return self.nutritional_notes
        return "Serve at room temperature, or warm for a few seconds to revive the aroma and softer center."

    @property
    def has_product_video(self) -> bool:
        return bool(self.product_video_embed_url)

    @property
    def product_video_kind(self) -> str:
        if self.primary_stack_video and self.primary_stack_video.video_file:
            return "direct"
        if self.video_file:
            return "direct"
        if not self.video_url:
            return ""
        parsed = urlparse(self.video_url)
        path = parsed.path.lower()
        if any(path.endswith(extension) for extension in (".mp4", ".webm", ".ogg")):
            return "direct"
        return ""

    @property
    def product_video_embed_url(self) -> str:
        if self.primary_stack_video and self.primary_stack_video.video_file:
            return self.primary_stack_video.video_file.url
        if self.video_file:
            return self.video_file.url
        if not self.video_url:
            return ""
        parsed = urlparse(self.video_url)
        if any(parsed.path.lower().endswith(extension) for extension in (".mp4", ".webm", ".ogg")):
            return self.video_url
        return ""

    @property
    def product_video_caption_display(self) -> str:
        return self.video_caption or f"A closer look at {self.name}, from crumb to finish."

    @property
    def product_video_poster_url(self) -> str:
        return self.primary_image.image.url if self.primary_image else ""


class ProductImage(TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="catalog/products/", blank=True)
    video_file = models.FileField(upload_to="catalog/products/videos/", blank=True)
    alt_text = models.CharField(max_length=180, blank=True)
    is_primary = models.BooleanField(default=False)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "product image"
        verbose_name_plural = "product images"

    def __str__(self) -> str:
        return f"{self.product.name} image"


class ProductVariant(TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    name = models.CharField(max_length=120)
    sku = models.CharField(max_length=64, unique=True)
    pack_size = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(99)]
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    compare_at_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    inventory_quantity = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=5)
    weight_grams = models.PositiveIntegerField(default=0)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "pack_size", "price"]
        verbose_name = "product variant"
        verbose_name_plural = "product variants"
        indexes = [
            models.Index(fields=["sku"]),
            models.Index(fields=["product", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.product.name} — {self.name}"

    @property
    def is_in_stock(self) -> bool:
        return self.inventory_quantity > 0 and self.is_active

    @property
    def is_low_stock(self) -> bool:
        return self.inventory_quantity <= self.low_stock_threshold
