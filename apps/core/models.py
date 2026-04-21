from django.core.validators import MinLengthValidator
from django.db import models
from django.utils.text import slugify


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SingletonModel(TimeStampedModel):
    singleton_name = "singleton"

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        return

    @classmethod
    def load(cls):
        # Singletons are read on every template render via the context
        # processor / CoreContextMixin. Cache for 60s to skip the round-trip
        # to Postgres; admin saves invalidate via the post_save signal below.
        from django.core.cache import cache

        cache_key = f"singleton:{cls._meta.label_lower}"
        obj = cache.get(cache_key)
        if obj is None:
            obj, _created = cls.objects.get_or_create(pk=1)
            cache.set(cache_key, obj, timeout=60)
        return obj

    @classmethod
    def _invalidate_singleton_cache(cls):
        from django.core.cache import cache

        cache.delete(f"singleton:{cls._meta.label_lower}")


class SiteSettings(SingletonModel):
    site_name = models.CharField(max_length=120, default="Nest & Whisk")
    tag_line = models.CharField(
        max_length=255,
        default="Premium handcrafted cookies delivered with warmth, elegance, and delight.",
    )
    meta_title = models.CharField(max_length=160, blank=True)
    meta_description = models.TextField(blank=True)
    announcement_bar_text = models.CharField(
        max_length=255,
        default="Delhi NCR delivery only - same-day/next-day in select areas.",
    )
    support_email = models.EmailField(default="hello@nestandwhisk.com")
    support_phone = models.CharField(max_length=32, blank=True)
    instagram_url = models.URLField(blank=True)
    tiktok_url = models.URLField(blank=True)
    pinterest_url = models.URLField(blank=True)
    footer_blurb = models.TextField(
        default=(
            "Nest & Whisk pairs the comfort of home baking with the elegance of handcrafted "
            "gifting—small-batch cookies, beautiful presentation, and a warm experience from "
            "first click to first bite."
        )
    )

    class Meta:
        verbose_name = "site settings"
        verbose_name_plural = "site settings"

    def __str__(self) -> str:
        return self.site_name


class HomepageContent(SingletonModel):
    eyebrow = models.CharField(max_length=120, default="Premium handcrafted cookies")
    hero_title = models.CharField(
        max_length=180, default="Delivered with warmth, elegance, and delight."
    )
    hero_body = models.TextField(
        default=(
            "Thoughtfully baked in small batches, beautifully packed for gifting, and made to "
            "turn ordinary moments into something worth savoring."
        )
    )
    primary_cta_label = models.CharField(max_length=50, default="Shop Now")
    primary_cta_url = models.CharField(max_length=255, default="#")
    secondary_cta_label = models.CharField(max_length=50, default="Build a Box")
    secondary_cta_url = models.CharField(max_length=255, default="#")
    tertiary_cta_label = models.CharField(max_length=50, default="Subscribe")
    tertiary_cta_url = models.CharField(max_length=255, default="#")
    feature_one_label = models.CharField(max_length=60, default="Bestseller")
    feature_one_title = models.CharField(max_length=120, default="Sea Salt Caramel")
    feature_one_body = models.TextField(
        default="Buttery centers, caramel notes, and a delicate salt finish."
    )
    feature_two_label = models.CharField(max_length=60, default="Seasonal")
    feature_two_title = models.CharField(max_length=120, default="Pistachio Rose")
    feature_two_body = models.TextField(
        default="Elegant floral notes with a soft nutty crunch."
    )
    feature_banner_label = models.CharField(max_length=60, default="Curated gifting")
    feature_banner_body = models.TextField(
        default=(
            "Luxury packaging, gift notes, and subscription-ready boxes designed to arrive "
            "beautifully."
        )
    )
    quality_title = models.CharField(max_length=120, default="Small-batch quality")
    quality_body_left = models.TextField(
        default="Premium chocolate, cultured butter, fragrant vanilla, and thoughtful finishing touches."
    )
    quality_body_right = models.TextField(
        default="Build-your-own boxes, curated subscriptions, and gifting experiences crafted to feel personal."
    )

    class Meta:
        verbose_name = "homepage content"
        verbose_name_plural = "homepage content"

    def __str__(self) -> str:
        return "Homepage content"


class PolicyPage(TimeStampedModel):
    title = models.CharField(max_length=150)
    slug = models.SlugField(max_length=160, unique=True)
    summary = models.CharField(max_length=255, blank=True)
    body = models.TextField(validators=[MinLengthValidator(40)])
    is_published = models.BooleanField(default=True)
    seo_title = models.CharField(max_length=160, blank=True)
    seo_description = models.CharField(max_length=255, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "title"]
        verbose_name = "policy page"
        verbose_name_plural = "policy pages"

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)


class FAQ(TimeStampedModel):
    question = models.CharField(max_length=255)
    answer = models.TextField()
    category = models.CharField(max_length=120, default="General")
    is_published = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "question"]
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"

    def __str__(self) -> str:
        return self.question


class Testimonial(TimeStampedModel):
    customer_name = models.CharField(max_length=120)
    customer_title = models.CharField(max_length=120, blank=True)
    quote = models.TextField()
    rating = models.PositiveSmallIntegerField(default=5)
    is_featured = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "customer_name"]

    def __str__(self) -> str:
        return self.customer_name


class ContactSettings(SingletonModel):
    page_title = models.CharField(max_length=150, default="We'd love to hear from you.")
    intro = models.TextField(
        default=(
            "Questions about gifting, events, subscriptions, or custom boxes? Our team is here to help."
        )
    )
    inquiry_email = models.EmailField(default="hello@nestandwhisk.com")
    business_hours = models.CharField(max_length=120, default="Mon–Sat · 9am–6pm")
    studio_location = models.CharField(max_length=160, blank=True)
    contact_card_body = models.TextField(
        default="Email us and we’ll get back to you promptly with thoughtful, personal support."
    )

    class Meta:
        verbose_name = "contact settings"
        verbose_name_plural = "contact settings"

    def __str__(self) -> str:
        return "Contact settings"


class NewsletterSignup(TimeStampedModel):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=80, blank=True)
    source = models.CharField(max_length=100, default="site")
    is_active = models.BooleanField(default=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "newsletter signup"
        verbose_name_plural = "newsletter signups"

    def __str__(self) -> str:
        return self.email


# Invalidate singleton caches when they're saved through admin, so edits are
# reflected within the 60s cache TTL window instantly.
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save)
def _invalidate_singleton_cache_on_save(sender, instance, **_):
    if isinstance(instance, SingletonModel):
        sender._invalidate_singleton_cache()

