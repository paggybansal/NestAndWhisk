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

if [ "${DJANGO_BOOTSTRAP_ADMIN:-0}" = "1" ]; then
  python manage.py bootstrap_admin
fi

exec gunicorn config.wsgi:application \
  --bind 0.0.0.0:"$PORT" \
  --workers "${GUNICORN_WORKERS:-3}" \
  --timeout "${GUNICORN_TIMEOUT:-120}" \
  --access-logfile - \
  --error-logfile -

