#!/bin/bash

echo "========================================"
echo "Starting Celery Beat for Linux/Mac"
echo "========================================"

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "WARNING: Virtual environment not found. Using system Python."
fi

# Check Redis connection
echo "Checking Redis connection..."
python -c "import redis; r = redis.Redis(host='localhost', port=6379); r.ping(); print('Redis OK!')" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "ERROR: Redis is not running!" >&2
    echo "Please install and start Redis first." >&2
    echo "See docs/CELERY_SETUP.md for instructions" >&2
    exit 1
fi

# Start Celery Beat
echo "Starting Celery Beat..."
cd fkapi
celery -A fkapi beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
cd ..
