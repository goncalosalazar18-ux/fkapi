#!/bin/bash

echo "========================================"
echo "Starting Celery Worker for Linux/Mac"
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
    echo "ERROR: Redis is not running!"
    echo "Please install and start Redis first."
    echo "See docs/CELERY_SETUP.md for instructions"
    exit 1
fi

# Start Celery Worker
echo "Starting Celery Worker..."
cd fkapi
python manage.py celery worker --loglevel=info --pool=threads --concurrency=4 || \
    python -m celery -A fkapi worker --loglevel=info --pool=threads --concurrency=4
cd ..
