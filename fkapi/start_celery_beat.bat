@echo off
echo ========================================
echo Starting Celery Beat for Windows
echo ========================================
cd /d %~dp0
call venv\Scripts\activate.bat

echo Checking Redis connection...
python -c "import redis; r = redis.Redis(host='localhost', port=6379); r.ping(); print('Redis OK!')" 2>nul
if errorlevel 1 (
    echo ERROR: Redis is not running!
    echo Please install and start Redis first.
    echo See INSTALL_REDIS_WINDOWS.md for instructions
    pause
    exit /b 1
)

echo Starting Celery Beat...
celery -A fkapi beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
pause
