#!/bin/sh
set -eu

exec celery -A config beat -l info

