#!/bin/sh
set -eu

for app_label in contenttypes auth catalog
do
  python manage.py migrate "$app_label" --noinput
done

python manage.py migrate --run-syncdb --noinput

for app_label in admin sessions sites
do
  python manage.py migrate "$app_label" --noinput
done

python manage.py migrate --noinput
python manage.py collectstatic --noinput --clear

if [ "${DJANGO_BOOTSTRAP_DEMO:-0}" = "1" ]; then
  python manage.py seed_demo_store
fi

if [ "${DJANGO_BOOTSTRAP_ADMIN:-0}" = "1" ]; then
  python manage.py bootstrap_admin
fi

exec gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "${GUNICORN_WORKERS:-3}" \
  --timeout "${GUNICORN_TIMEOUT:-120}" \
  --access-logfile - \
  --error-logfile -

