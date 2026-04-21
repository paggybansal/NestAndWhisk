#!/bin/sh
set -eu

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings.prod}"
PORT="${PORT:-8000}"
RUN_MIGRATIONS_ON_BOOT="${DJANGO_RUN_MIGRATIONS_ON_BOOT:-1}"
COLLECTSTATIC_ON_BOOT="${DJANGO_COLLECTSTATIC_ON_BOOT:-1}"

if [ "$RUN_MIGRATIONS_ON_BOOT" = "1" ]; then
  # One call: Django's migration framework resolves the dependency graph
  # itself (e.g. accounts.User must precede admin.0001_initial). Manual
  # per-app ordering used to be a workaround for --run-syncdb drift; it is
  # no longer needed and actively breaks ordering when AUTH_USER_MODEL is
  # custom. --fake-initial is idempotent and harmless on a fresh DB.
  python manage.py migrate --noinput --fake-initial
fi

if [ "$COLLECTSTATIC_ON_BOOT" = "1" ]; then
  python manage.py collectstatic --noinput --clear
fi

if [ "${DJANGO_BOOTSTRAP_DEMO:-0}" = "1" ]; then
  python manage.py seed_demo_store
fi

# One-shot data import:
#   - DJANGO_LOAD_FIXTURE: always load (use once then unset).
#   - DJANGO_AUTOLOAD_FIXTURE: load only when the catalog is empty
#     (safe to keep permanently — re-loads a fresh DB on first boot only).
if [ -n "${DJANGO_LOAD_FIXTURE:-}" ]; then
  echo "Loading fixture from $DJANGO_LOAD_FIXTURE ..."
  python manage.py loaddata "$DJANGO_LOAD_FIXTURE"
elif [ -n "${DJANGO_AUTOLOAD_FIXTURE:-}" ] && [ -f "$DJANGO_AUTOLOAD_FIXTURE" ]; then
  product_count=$(python manage.py shell -c "from apps.catalog.models import Product; print(Product.objects.count())" 2>/dev/null | tail -n 1)
  if [ "$product_count" = "0" ]; then
    echo "DB has 0 products; auto-loading $DJANGO_AUTOLOAD_FIXTURE ..."
    python manage.py loaddata "$DJANGO_AUTOLOAD_FIXTURE"
  else
    echo "DB already has $product_count products; skipping auto-load."
  fi
fi

if [ "${DJANGO_BOOTSTRAP_ADMIN:-0}" = "1" ]; then
  python manage.py bootstrap_admin
fi

# Non-fatal Redis connectivity probe so deploy logs clearly state whether the
# shared cache is live or the app is running on per-process LocMem.
python -c "
import os, django, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.prod')
django.setup()
from django.core.cache import cache
from django.conf import settings
backend = settings.CACHES['default']['BACKEND']
try:
    cache.set('__boot_probe__', '1', 10)
    ok = cache.get('__boot_probe__') == '1'
    print(f'[cache] backend={backend} probe={\"OK\" if ok else \"FAIL\"}')
except Exception as exc:
    print(f'[cache] backend={backend} probe=ERROR error={exc!r}', file=sys.stderr)
" || true

exec gunicorn config.wsgi:application \
  --bind 0.0.0.0:"$PORT" \
  --worker-class "${GUNICORN_WORKER_CLASS:-gthread}" \
  --workers "${GUNICORN_WORKERS:-2}" \
  --threads "${GUNICORN_THREADS:-8}" \
  --timeout "${GUNICORN_TIMEOUT:-60}" \
  --graceful-timeout "${GUNICORN_GRACEFUL_TIMEOUT:-30}" \
  --keep-alive "${GUNICORN_KEEPALIVE:-5}" \
  --max-requests "${GUNICORN_MAX_REQUESTS:-1000}" \
  --max-requests-jitter "${GUNICORN_MAX_REQUESTS_JITTER:-100}" \
  --access-logfile - \
  --error-logfile -

