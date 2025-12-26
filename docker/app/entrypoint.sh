#!/bin/sh
set -e

# Run migrations
python manage.py migrate --noinput

# Collect static files (if needed)
python manage.py collectstatic --noinput || true

# Execute the command passed to the entrypoint
exec "$@"

