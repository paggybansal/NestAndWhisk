# Nest & Whisk

Premium artisan cookie e-commerce platform built with Django, Tailwind, and Vite.

## Local development quick start

Install Python dependencies and validate Django:

```powershell
python -m pip install -r requirements\dev.txt
python manage.py check
```

## Docker deployment quick start

This repository now ships with a production-oriented Docker setup:

- multi-stage image build
- Vite assets compiled into the image
- Gunicorn serving Django
- PostgreSQL + Redis + Celery worker + Celery beat
- automatic `migrate --run-syncdb` + `collectstatic` on container boot

1. Create a Docker env file from the example:

```powershell
Copy-Item .env.example .env
```

2. For first boot, optionally enable demo data and admin bootstrap in `.env`:

```dotenv
DJANGO_BOOTSTRAP_DEMO=1
DJANGO_BOOTSTRAP_ADMIN=1
```

3. Build and start the stack:

```powershell
docker compose up --build
```

4. Open the app:

- storefront: `http://127.0.0.1:8000/`
- healthcheck: `http://127.0.0.1:8000/health/`
- admin: `http://127.0.0.1:8000/admin/login/`

Useful Docker commands:

```powershell
docker compose ps
docker compose logs -f web
docker compose logs -f celery_worker
docker compose exec web python manage.py check
docker compose down
```

If Docker Desktop is installed but the engine is not responding on Windows, restart Docker Desktop and confirm Linux containers are running before retrying `docker compose up --build`.

## One-command local preview setup

This project includes a local bootstrap command that:

- builds frontend assets
- runs `migrate --run-syncdb`
- seeds demo storefront content
- creates or refreshes the admin user

Run it with:

```powershell
python manage.py local_setup --install-frontend
```

Then start the site:

```powershell
python manage.py runserver 127.0.0.1:8001
```

Open:

- storefront: `http://127.0.0.1:8001/`
- admin: `http://127.0.0.1:8001/admin/login/`

Default local admin credentials:

- email: `admin@nestandwhisk.com`
- password: `ChangeMe123!`

## Useful local commands

Re-seed demo merchandising content:

```powershell
python manage.py seed_demo_store
```

Refresh only the admin user:

```powershell
python manage.py bootstrap_admin
```

Skip optional parts of the bootstrap flow:

```powershell
python manage.py local_setup --skip-assets
python manage.py local_setup --skip-admin
python manage.py local_setup --skip-seed
```

## Local payment testing

Checkout supports two local testing modes:

- `Stripe test mode` for the hosted Stripe checkout flow
- `Mock payment simulator` for local success / failure / cancellation testing without a gateway

Example `.env` values:

```dotenv
MOCK_PAYMENT_ENABLED=True
DEFAULT_PAYMENT_PROVIDER=stripe
STRIPE_CURRENCY=inr
STRIPE_ENABLE_UPI=True
```

When mock mode is enabled, checkout lets you choose between Stripe test mode and the local mock simulator.

## Optional AI FAQ assistant

The FAQ page includes an isolated support chat panel at `/faq/`.

- By default it uses grounded FAQ/policy retrieval only.
- If you enable AI settings, it can refine answers with Gemini while staying grounded in your store content.

Example `.env` values:

```dotenv
AI_CHAT_ENABLED=True
AI_CHAT_PROVIDER=gemini
AI_CHAT_MODEL=gemini-2.0-flash
AI_CHAT_API_KEY=your_api_key_here
AI_CHAT_BASE_URL=https://generativelanguage.googleapis.com/v1beta
AI_CHAT_TIMEOUT_SECONDS=12
AI_CHAT_PROJECT_NAME=projects/your-project-number
AI_CHAT_PROJECT_NUMBER=your-project-number
```

If the API key is missing or the AI request fails, the assistant falls back automatically to the built-in FAQ/policy answer engine.

## Optional Shiprocket live delivery ETA lookup

Checkout can optionally request a real-time courier estimate from Shiprocket while still falling back to the built-in Delhi NCR delivery guidance when the API is unavailable or not configured.

Example `.env` values:

```dotenv
SHIPROCKET_ENABLED=True
SHIPROCKET_EMAIL=ops@example.com
SHIPROCKET_PASSWORD=your_shiprocket_password
SHIPROCKET_PICKUP_POSTCODE=110020
SHIPROCKET_DEFAULT_PACKAGE_WEIGHT_KG=0.5
SHIPROCKET_TIMEOUT_SECONDS=8
```

When enabled, checkout uses the customer city and postal code to query Shiprocket courier serviceability and ETA in real time.

## Railway deployment

This repo can be deployed to Railway using the included `Dockerfile` and startup scripts.

### Recommended Railway services

Create one Railway project with:

- `web` (public)
- `postgres` (Railway Postgres)
- `redis` (Railway Redis)
- `celery-worker` (private)
- `celery-beat` (private)

Use the same GitHub repo for all three app services.

### Branch

- repository: `https://github.com/paggybansal/NestAndWhisk.git`
- branch: `master`

### Service commands

`web` can use the default Docker command because `docker/web/entrypoint.sh` now honors Railway's `PORT`.

For the background services, override the Railway start command:

```sh
/app/docker/celery/worker-entrypoint.sh
```

```sh
/app/docker/celery/beat-entrypoint.sh
```

### Web health check

Set the Railway health check path to:

```text
/health/
```

### Required environment variables

Set these on `web`, `celery-worker`, and `celery-beat` unless noted:

```dotenv
DJANGO_SETTINGS_MODULE=config.settings.prod
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=<generate a strong secret>
DATABASE_URL=<Railway Postgres DATABASE_URL>
REDIS_URL=<Railway Redis URL>
CELERY_BROKER_URL=<Railway Redis URL>
CELERY_RESULT_BACKEND=<Railway Redis URL>
USE_REDIS_CACHE=True
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
DJANGO_VITE_DEV_MODE=False
DJANGO_BOOTSTRAP_DEMO=0
DJANGO_BOOTSTRAP_ADMIN=1
DJANGO_SUPERUSER_EMAIL=admin@nestandwhisk.com
DJANGO_SUPERUSER_PASSWORD=<set in Railway>
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=<your smtp host>
EMAIL_PORT=587
EMAIL_HOST_USER=<your smtp username>
EMAIL_HOST_PASSWORD=<set in Railway>
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL="Nest & Whisk <hello@nestandwhisk.com>"
SERVER_EMAIL=server@nestandwhisk.com
RAILWAY_PUBLIC_DOMAIN=<auto-filled by Railway on web>
STRIPE_PUBLIC_KEY=<Stripe test publishable key>
STRIPE_SECRET_KEY=<Stripe test secret key>
STRIPE_WEBHOOK_SECRET=<Stripe test webhook secret>
SHIPROCKET_ENABLED=True
SHIPROCKET_EMAIL=<set in Railway>
SHIPROCKET_PASSWORD=<set in Railway>
SHIPROCKET_PICKUP_POSTCODE=<your pickup postal code>
AI_CHAT_ENABLED=True
AI_CHAT_PROVIDER=gemini
AI_CHAT_MODEL=gemini-2.0-flash
AI_CHAT_API_KEY=<set in Railway>
SENTRY_DSN=<set in Railway>
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.0
```

You can leave `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS` empty if you rely on `RAILWAY_PUBLIC_DOMAIN`; the app automatically adds the Railway domain when that variable is present. Add those variables explicitly later when you move to a custom domain.

### Generating a Django secret key

Run this locally:

```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Copy the output into Railway as `DJANGO_SECRET_KEY`.

### Best simple free media option

For the simplest free option, use **Cloudinary** for uploaded media. Railway's filesystem is ephemeral, so local `media/` storage is only suitable for short-lived demos.

### Important production caveats

- `web` currently runs migrations and `collectstatic` on boot. This is fine for a single web instance, but move those to a release step before scaling horizontally.
- `celery-beat` should stay at **one instance only**.
- The current Celery beat scheduler uses local persistent state; it works, but `django-celery-beat` is a better long-term fit for Railway.
- `SERVE_MEDIA_FILES=True` is okay only for demos. Use Cloudinary/S3/R2 for production uploads.

