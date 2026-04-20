from pathlib import Path

import environ
from celery.schedules import crontab
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parents[2]
APPS_DIR = BASE_DIR / "apps"
env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    SECURE_SSL_REDIRECT=(bool, False),
    SESSION_COOKIE_SECURE=(bool, False),
    CSRF_COOKIE_SECURE=(bool, False),
    USE_REDIS_CACHE=(bool, True),
    DJANGO_VITE_DEV_MODE=(bool, False),
    AI_CHAT_ENABLED=(bool, False),
    SERVE_MEDIA_FILES=(bool, False),
    EMAIL_PORT=(int, 587),
    EMAIL_USE_TLS=(bool, True),
    EMAIL_USE_SSL=(bool, False),
    SENTRY_TRACES_SAMPLE_RATE=(float, 0.0),
)

environ.Env.read_env(BASE_DIR / ".env")

DEBUG = env("DJANGO_DEBUG")
SECRET_KEY = env("DJANGO_SECRET_KEY", default="unsafe-secret-key")
ALLOWED_HOSTS = env.list(
    "DJANGO_ALLOWED_HOSTS",
    default=["127.0.0.1", "localhost", "testserver"],
)
CSRF_TRUSTED_ORIGINS = env.list(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    default=["http://127.0.0.1:8000", "http://localhost:8000"],
)
RAILWAY_PUBLIC_DOMAIN = env("RAILWAY_PUBLIC_DOMAIN", default="")
if RAILWAY_PUBLIC_DOMAIN:
    if RAILWAY_PUBLIC_DOMAIN not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(RAILWAY_PUBLIC_DOMAIN)
    railway_origin = f"https://{RAILWAY_PUBLIC_DOMAIN}"
    if railway_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(railway_origin)

SITE_ID = env.int("SITE_ID", default=1)

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.contrib.humanize",
    "django.contrib.sitemaps",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "django_filters",
    "django_htmx",
    "django_vite",
    "widget_tweaks",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
]

LOCAL_APPS = [
    "apps.core",
    "apps.accounts",
    "apps.catalog",
    "apps.cart",
    "apps.checkout",
    "apps.orders",
    "apps.subscriptions",
    "apps.reviews",
    "apps.blog",
    "apps.corporate",
    "apps.marketing",
    "apps.api",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.shared_site_context",
                "apps.cart.context_processors.cart_snapshot",
            ],
        },
    }
]

database_url = env("DATABASE_URL", default="").strip()
if database_url:
    default_database_config = env.db_url("DATABASE_URL")
elif DEBUG:
    default_database_config = env.db_url(
        "DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
    )
else:
    raise ImproperlyConfigured(
        "DATABASE_URL is missing or empty. In Railway, set DATABASE_URL to your Postgres service reference before deploying the web or Celery services."
    )

DATABASES = {"default": default_database_config}
DATABASES["default"]["ATOMIC_REQUESTS"] = True

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
SERVE_MEDIA_FILES = env.bool("SERVE_MEDIA_FILES", default=DEBUG)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

LOGIN_REDIRECT_URL = "account_dashboard"
LOGOUT_REDIRECT_URL = "home"
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_FORMS = {
    "login": "apps.accounts.forms.CustomerLoginForm",
    "signup": "apps.accounts.forms.CustomerSignupForm",
    "reset_password": "apps.accounts.forms.CustomerResetPasswordForm",
}
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_VERIFICATION = "optional"
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_SESSION_REMEMBER = True

EMAIL_BACKEND = env(
    "EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=False)
DEFAULT_FROM_EMAIL = env(
    "DEFAULT_FROM_EMAIL", default="Nest & Whisk <hello@nestandwhisk.com>"
)
SERVER_EMAIL = env("SERVER_EMAIL", default="server@nestandwhisk.com")

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
}

REDIS_URL = env("REDIS_URL", default="redis://127.0.0.1:6379/0")
USE_REDIS_CACHE = env.bool("USE_REDIS_CACHE", default=True)

# Guard against misconfigured REDIS_URL on PaaS (e.g. unresolved
# "${{Redis.REDIS_URL}}" reference, bare host, or empty string). If the value
# is not a valid redis scheme, silently fall back to a local in-memory cache
# so the app still boots instead of 500ing on every request.
_valid_redis_schemes = ("redis://", "rediss://", "unix://")
if USE_REDIS_CACHE and not (REDIS_URL and REDIS_URL.startswith(_valid_redis_schemes)):
    import logging as _logging
    _logging.getLogger(__name__).warning(
        "USE_REDIS_CACHE is true but REDIS_URL=%r is not a valid redis scheme; "
        "falling back to local-memory cache and DB sessions.",
        REDIS_URL,
    )
    USE_REDIS_CACHE = False

if USE_REDIS_CACHE:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
        }
    }
    SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "nest-and-whisk-local",
        }
    }
    SESSION_ENGINE = "django.contrib.sessions.backends.db"

_redis_available = REDIS_URL and REDIS_URL.startswith(_valid_redis_schemes)
CELERY_BROKER_URL = env(
    "CELERY_BROKER_URL", default=REDIS_URL if _redis_available else "memory://"
)
CELERY_RESULT_BACKEND = env(
    "CELERY_RESULT_BACKEND",
    default="redis://127.0.0.1:6379/1" if _redis_available and USE_REDIS_CACHE else "cache+memory://",
)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = "celery.beat:PersistentScheduler"
CELERY_BEAT_SCHEDULE = {
    "subscriptions-refresh-schedules": {
        "task": "apps.subscriptions.tasks.refresh_subscription_schedules_task",
        "schedule": crontab(hour=2, minute=0),
    },
    "subscriptions-create-shipments": {
        "task": "apps.subscriptions.tasks.create_subscription_shipments_task",
        "schedule": crontab(hour=3, minute=0),
    },
}

STRIPE_PUBLIC_KEY = env("STRIPE_PUBLIC_KEY", default="")
STRIPE_SECRET_KEY = env("STRIPE_SECRET_KEY", default="")
STRIPE_WEBHOOK_SECRET = env("STRIPE_WEBHOOK_SECRET", default="")
STRIPE_CURRENCY = env("STRIPE_CURRENCY", default="inr")
STRIPE_ENABLE_UPI = env.bool("STRIPE_ENABLE_UPI", default=STRIPE_CURRENCY.lower() == "inr")
MOCK_PAYMENT_ENABLED = env.bool("MOCK_PAYMENT_ENABLED", default=DEBUG)
DEFAULT_PAYMENT_PROVIDER = env("DEFAULT_PAYMENT_PROVIDER", default="stripe")

# ---- PhonePe PG Checkout V2 (OAuth client_credentials) ----
PHONEPE_ENV = env("PHONEPE_ENV", default="SANDBOX").upper()  # SANDBOX | PRODUCTION
# V2 credentials (preferred). Fallback to legacy MERCHANT_ID / SALT_KEY names
# so an existing .env keeps working during the V1 → V2 migration.
PHONEPE_CLIENT_ID = env("PHONEPE_CLIENT_ID", default="") or env("PHONEPE_MERCHANT_ID", default="")
PHONEPE_CLIENT_SECRET = env("PHONEPE_CLIENT_SECRET", default="") or env("PHONEPE_SALT_KEY", default="")
PHONEPE_CLIENT_VERSION = env("PHONEPE_CLIENT_VERSION", default="1")
# Callback auth (configured in PhonePe dashboard → Webhooks).
# Callback Authorization header = sha256(username + ":" + password) as hex.
PHONEPE_CALLBACK_USERNAME = env("PHONEPE_CALLBACK_USERNAME", default="")
PHONEPE_CALLBACK_PASSWORD = env("PHONEPE_CALLBACK_PASSWORD", default="")
PHONEPE_BASE_URL_SANDBOX = env(
    "PHONEPE_BASE_URL_SANDBOX",
    default="https://api-preprod.phonepe.com/apis/pg-sandbox",
)
PHONEPE_BASE_URL_PRODUCTION = env(
    "PHONEPE_BASE_URL_PRODUCTION",
    default="https://api.phonepe.com/apis/pg",
)
# PhonePe V2 auth endpoint uses a dedicated host in production ("identity-manager")
# while sandbox serves auth on the same base as the data-plane. We therefore
# allow both to be configured independently; the sandbox default is fine.
PHONEPE_AUTH_BASE_URL_SANDBOX = env(
    "PHONEPE_AUTH_BASE_URL_SANDBOX",
    default="https://api-preprod.phonepe.com/apis/pg-sandbox",
)
PHONEPE_AUTH_BASE_URL_PRODUCTION = env(
    "PHONEPE_AUTH_BASE_URL_PRODUCTION",
    default="https://api.phonepe.com/apis/identity-manager",
)
PHONEPE_TIMEOUT_SECONDS = env.int("PHONEPE_TIMEOUT_SECONDS", default=15)

SHIPROCKET_ENABLED = env.bool("SHIPROCKET_ENABLED", default=False)
SHIPROCKET_BASE_URL = env(
    "SHIPROCKET_BASE_URL",
    default="https://apiv2.shiprocket.in/v1/external",
)
SHIPROCKET_EMAIL = env("SHIPROCKET_EMAIL", default="")
SHIPROCKET_PASSWORD = env("SHIPROCKET_PASSWORD", default="")
SHIPROCKET_PICKUP_POSTCODE = env("SHIPROCKET_PICKUP_POSTCODE", default="")
SHIPROCKET_DEFAULT_PACKAGE_WEIGHT_KG = env.float("SHIPROCKET_DEFAULT_PACKAGE_WEIGHT_KG", default=0.5)
SHIPROCKET_TIMEOUT_SECONDS = env.int("SHIPROCKET_TIMEOUT_SECONDS", default=8)

AI_CHAT_ENABLED = env.bool("AI_CHAT_ENABLED", default=False)
AI_CHAT_PROVIDER = env("AI_CHAT_PROVIDER", default="gemini")
AI_CHAT_MODEL = env("AI_CHAT_MODEL", default="gemini-2.0-flash")
AI_CHAT_API_KEY = env("AI_CHAT_API_KEY", default="")
AI_CHAT_BASE_URL = env("AI_CHAT_BASE_URL", default="https://generativelanguage.googleapis.com/v1beta")
AI_CHAT_TIMEOUT_SECONDS = env.int("AI_CHAT_TIMEOUT_SECONDS", default=12)

DJANGO_VITE = {
    "default": {
        "dev_mode": env.bool("DJANGO_VITE_DEV_MODE", default=DEBUG),
        "dev_server_protocol": "http",
        "dev_server_host": "localhost",
        "dev_server_port": 5173,
        "static_url_prefix": "build",
        "manifest_path": BASE_DIR / "static" / "build" / "manifest.json",
    }
}

SENTRY_DSN = env("SENTRY_DSN", default="")
SENTRY_ENVIRONMENT = env("SENTRY_ENVIRONMENT", default="development" if DEBUG else "production")
SENTRY_TRACES_SAMPLE_RATE = env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.0)

def _initialize_sentry() -> None:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.django import DjangoIntegration
    except ImportError:
        return
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=SENTRY_ENVIRONMENT,
        traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
        send_default_pii=True,
        integrations=[DjangoIntegration(), CeleryIntegration()],
    )


if SENTRY_DSN:
    _initialize_sentry()

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_SSL_REDIRECT = env("SECURE_SSL_REDIRECT")
# Exempt health check and well-known paths so Railway's internal HTTP health
# probe (which does not follow redirects) isn't 301'd to HTTPS.
SECURE_REDIRECT_EXEMPT = [r"^health/$", r"^\.well-known/"]
SESSION_COOKIE_SECURE = env("SESSION_COOKIE_SECURE")
CSRF_COOKIE_SECURE = env("CSRF_COOKIE_SECURE")
SESSION_COOKIE_SAMESITE = env("COOKIE_SAMESITE", default="Lax")
CSRF_COOKIE_SAMESITE = env("COOKIE_SAMESITE", default="Lax")

ADMIN_URL = "admin/"

# Ensure unhandled exceptions (500s) are logged to stderr so they appear in
# Railway/Docker logs. Without this, Django's default only mails admins.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.server": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

