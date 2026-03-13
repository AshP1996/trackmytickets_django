#!/bin/bash
set -e

# Wait for DB to be ready (handles pgbouncer/db startup race)
echo "Waiting for database..."
until python manage.py showmigrations 2>/dev/null | head -1 > /dev/null; do
  sleep 2
done
echo "Database is ready."

# Run migrations (creates global_users, etc. if missing)
echo "Running migrations..."
python manage.py migrate --noinput

# Collect static (idempotent; needed if volume is empty)
python manage.py collectstatic --noinput 2>/dev/null || true

# Start the main process
exec "$@"
