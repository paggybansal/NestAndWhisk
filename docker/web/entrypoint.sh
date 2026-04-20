#!/bin/sh
set -eu

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings.prod}"
PORT="${PORT:-8000}"
RUN_MIGRATIONS_ON_BOOT="${DJANGO_RUN_MIGRATIONS_ON_BOOT:-1}"
COLLECTSTATIC_ON_BOOT="${DJANGO_COLLECTSTATIC_ON_BOOT:-1}"

if [ "$RUN_MIGRATIONS_ON_BOOT" = "1" ]; then
  # Bootstrap the dependency-heavy apps first so later apps can reference
  # contenttypes/auth/catalog foreign keys cleanly. --fake-initial is safe
  # because migrations are idempotent: it only marks initial migrations as
  # applied when their target tables already exist *and* the schema matches.
  for app_label in contenttypes auth catalog
  do
    python manage.py migrate "$app_label" --noinput --fake-initial
  done


  for app_label in admin sessions sites
  do
    python manage.py migrate "$app_label" --noinput --fake-initial
  done

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

