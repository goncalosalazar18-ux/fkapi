@echo off
echo ========================================
echo Starting Celery Worker for Windows
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

echo Starting Celery Worker...
cd fkapi
python manage.py celeryd_multi start w1 -A fkapi --loglevel=info --pool=threads --concurrency=4 2>nul || python -m celery -A fkapi worker --loglevel=info --pool=threads --concurrency=4
cd ..
pause
