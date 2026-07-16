#!/bin/sh
set -e

echo "Waiting for PostgreSQL..."
if [ -n "$DATABASE_URL" ]; then
  PG_HOST=$(echo "$DATABASE_URL" | sed -n 's|.*@\([^:/]*\).*|\1|p')
  PG_PORT=$(echo "$DATABASE_URL" | sed -n 's|.*:\([0-9]*\)/.*|\1|p')
else
  PG_HOST="${DB_HOST:-db}"
  PG_PORT="${DB_PORT:-5432}"
fi
until pg_isready -h "$PG_HOST" -p "$PG_PORT" -U "${DB_USER}" 2>/dev/null; do
  echo "  $PG_HOST:$PG_PORT - no response"
  sleep 1
done
echo "  $PG_HOST:$PG_PORT - ready"

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting Gunicorn..."
exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers 3 \
    --timeout 120
