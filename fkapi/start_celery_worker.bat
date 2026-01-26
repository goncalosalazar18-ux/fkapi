@echo off
echo ========================================
echo Starting Celery Worker for Windows
echo ========================================
cd /d %~dp0

REM Try to activate venv from project root
if exist ..\venv\Scripts\activate.bat (
    call ..\venv\Scripts\activate.bat
) else if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo WARNING: Virtual environment not found. Make sure venv is activated.
)

echo Checking Redis connection...
python -c "import redis; r = redis.Redis(host='localhost', port=6379); r.ping(); print('Redis OK!')" 2>nul
if errorlevel 1 (
    echo WARNING: Redis connection failed, but continuing anyway...
    echo Celery will use database as fallback if Redis is not available.
)

echo Starting Celery Worker...
echo Command: celery -A fkapi worker --loglevel=info --pool=threads --concurrency=4
celery -A fkapi worker --loglevel=info --pool=threads --concurrency=4

pause
