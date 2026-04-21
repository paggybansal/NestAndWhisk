from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "Core"

    def ready(self):
        # Register cache-bust signal handlers (PolicyPage, Product, Testimonial,
        # SubscriptionPlan, BlogPost). Import side-effect is the whole point.
        from apps.core import signals  # noqa: F401

