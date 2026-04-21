from .base import *  # noqa: F403, F401

DEBUG = False
# Only force SMTP when an EMAIL_HOST is actually configured; otherwise keep
# the console backend so checkout isn't blocked by a non-existent mail server.
if env("EMAIL_HOST", default=""):
    EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=True)
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=True)
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
# Serve /media/* via Django so committed brand assets (Logo etc.) work without
# an external bucket. Suitable for low-traffic; switch to S3/R2 for real
# user-uploaded content at scale.
SERVE_MEDIA_FILES = env.bool("SERVE_MEDIA_FILES", default=True)

