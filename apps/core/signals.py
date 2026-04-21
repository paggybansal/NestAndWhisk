"""
Signals that drop view-layer caches whenever the backing model changes.

Keeps admin edits visible immediately rather than waiting for the TTL to
lapse. Kept deliberately coarse-grained (one key per fragment, no diffing)
since the underlying data is small and recomputation is cheap.
"""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.blog.models import BlogPost
from apps.catalog.models import Product
from apps.core.cache import bust
from apps.core.models import PolicyPage, Testimonial
from apps.subscriptions.models import SubscriptionPlan


@receiver([post_save, post_delete], sender=PolicyPage)
def _bust_footer_policies(sender, instance, **_):  # noqa: ARG001
    bust("core:footer_policies")


@receiver([post_save, post_delete], sender=Testimonial)
def _bust_testimonials(sender, instance, **_):  # noqa: ARG001
    bust("home:featured_testimonials")


@receiver([post_save, post_delete], sender=Product)
def _bust_product_lists(sender, instance, **_):  # noqa: ARG001
    bust("home:featured_products", "home:seasonal_products")


@receiver([post_save, post_delete], sender=SubscriptionPlan)
def _bust_plan(sender, instance, **_):  # noqa: ARG001
    bust("home:featured_plan")


@receiver([post_save, post_delete], sender=BlogPost)
def _bust_latest_posts(sender, instance, **_):  # noqa: ARG001
    bust("home:latest_posts")

