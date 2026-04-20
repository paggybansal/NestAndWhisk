from importlib.util import find_spec

from .base import *  # noqa: F403, F401

DEBUG = True
# EMAIL_BACKEND is now controlled by .env (base.py reads it).
# Set EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend in .env
# if you want emails to go to the console instead of real SMTP.

if find_spec("debug_toolbar") is not None:
    INSTALLED_APPS += ["debug_toolbar"]  # noqa: F405
    MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware", *MIDDLEWARE]  # noqa: F405

INTERNAL_IPS = ["127.0.0.1", "localhost"]

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

