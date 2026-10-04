#!/bin/sh
set -e

echo "Starting Comeia application..."

# Wait for PostgreSQL database if configured
if [ -n "$POSTGRES_HOST" ] || [ -n "$DATABASE_URL" ]; then
    echo "Waiting for PostgreSQL database to be ready..."
    
    DB_HOST="${POSTGRES_HOST:-db}"
    DB_PORT="${POSTGRES_PORT:-5432}"

    # Use python check to verify DB connectivity
    python << END
import sys
import time
import os

try:
    import psycopg
except ImportError:
    try:
        import psycopg2 as psycopg
    except ImportError:
        psycopg = None

if psycopg:
    host = os.environ.get("POSTGRES_HOST", "db")
    port = int(os.environ.get("POSTGRES_PORT", 5432))
    dbname = os.environ.get("POSTGRES_DB", "comeia")
    user = os.environ.get("POSTGRES_USER", "comeia_user")
    password = os.environ.get("POSTGRES_PASSWORD", "")
    
    for attempt in range(1, 31):
        try:
            conn = psycopg.connect(
                host=host,
                port=port,
                dbname=dbname,
                user=user,
                password=password,
                connect_timeout=3
            )
            conn.close()
            print("PostgreSQL is ready!")
            sys.exit(0)
        except Exception as e:
            print(f"Waiting for database... (attempt {attempt}/30): {e}")
            time.sleep(1)
    
    print("Database connection timed out, continuing anyway...")
END
fi

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear || python manage.py collectstatic --noinput

echo "Database migrations and static collection complete."

# Execute CMD
exec "$@"
