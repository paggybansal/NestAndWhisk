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

