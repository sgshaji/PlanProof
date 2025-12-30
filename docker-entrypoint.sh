#!/bin/bash
set -e

echo "==================================="
echo "PlanProof Docker Container Starting"
echo "==================================="

# Wait for database to be ready
if [ -n "$DATABASE_URL" ]; then
    echo "Waiting for database..."
    until pg_isready -h postgres -U planproof > /dev/null 2>&1; do
        echo "Database is unavailable - sleeping"
        sleep 2
    done
    echo "✓ Database is ready"
    
    # Run database migrations
    echo "Running database migrations..."
    alembic upgrade head
    echo "✓ Migrations complete"
fi

# Execute the main command
echo "Starting application..."
exec "$@"
