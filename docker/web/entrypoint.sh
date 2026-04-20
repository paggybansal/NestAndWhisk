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
  echo "===== STATIC SOURCE: /app/static/build/assets ====="
  ls -la /app/static/build/assets 2>&1 || echo "(missing)"
  echo "===== MEDIA SOURCE: /app/media (top level) ====="
  ls -la /app/media 2>&1 || echo "(missing)"
  python manage.py collectstatic --noinput --clear
  echo "===== STATIC COLLECTED: /app/staticfiles/build/assets ====="
  ls -la /app/staticfiles/build/assets 2>&1 || echo "(missing)"
fi

if [ "${DJANGO_BOOTSTRAP_DEMO:-0}" = "1" ]; then
  python manage.py seed_demo_store
fi

# One-shot data import:
#   - If DJANGO_LOAD_FIXTURE is set explicitly, always load that file.
#   - Otherwise, if DJANGO_AUTOLOAD_FIXTURE points to a path AND the catalog
#     is empty (no Product rows), load it. Lets a fresh DB get the local
#     dataset on first boot without re-importing on every deploy.
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

exec gunicorn config.wsgi:application \
  --bind 0.0.0.0:"$PORT" \
  --workers "${GUNICORN_WORKERS:-3}" \
  --timeout "${GUNICORN_TIMEOUT:-120}" \
  --access-logfile - \
  --error-logfile -

