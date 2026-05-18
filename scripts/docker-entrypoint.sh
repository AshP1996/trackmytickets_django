#!/bin/bash
set -euo pipefail

echo "Waiting for database..."
until python - <<'PY'
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", os.environ.get("DJANGO_SETTINGS_MODULE", "config.settings.prod_override"))
django.setup()
from django.db import connection

connection.ensure_connection()
PY
do
  sleep 2
done
echo "Database is ready."

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  echo "Running migrations..."
  python manage.py migrate --noinput
fi

if [ "${RUN_COLLECTSTATIC:-true}" = "true" ]; then
  python manage.py collectstatic --noinput 2>/dev/null || true
fi

exec "$@"
