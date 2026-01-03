#!/bin/bash
set -e

echo "==================================="
echo "PlanProof Docker Container Starting"
echo "==================================="

# Wait for database to be ready (if using Azure PostgreSQL, skip local check)
if [ -n "$DATABASE_URL" ]; then
    echo "Database URL configured: $DATABASE_URL"
    
    # Extract host from DATABASE_URL if it's not localhost/postgres
    if [[ "$DATABASE_URL" != *"localhost"* ]] && [[ "$DATABASE_URL" != *"postgres:"* ]]; then
        echo "Using external database (Azure PostgreSQL)"
    else
        echo "Waiting for local database..."
        until pg_isready -h postgres -U planproof > /dev/null 2>&1; do
            echo "Database is unavailable - sleeping"
            sleep 2
        done
        echo "✓ Database is ready"
    fi
    
    # Run database migrations
    echo "Running database migrations..."
    alembic upgrade head || echo "Warning: Migration failed or not needed"
    echo "✓ Migrations complete"
fi

# Execute the main command
echo "Starting application..."
exec "$@"
