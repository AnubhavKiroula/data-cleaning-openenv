#!/bin/bash
set -e

echo "Waiting for PostgreSQL to be ready..."

# Wait for PostgreSQL to be ready
max_retries=30
counter=0

until PGPASSWORD=$POSTGRES_PASSWORD psql -h postgres -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q' 2>/dev/null; do
    counter=$((counter + 1))
    if [ $counter -ge $max_retries ]; then
        echo "Error: PostgreSQL did not become ready in time"
        exit 1
    fi
    echo "Waiting for PostgreSQL... ($counter/$max_retries)"
    sleep 2
done

echo "PostgreSQL is ready!"

# Run database migrations
echo "Running database migrations..."
python -m alembic upgrade head || echo "No migrations to run or alembic not configured"

# Start the application
echo "Starting FastAPI application..."
exec python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000
