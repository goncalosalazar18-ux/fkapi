# Celery Setup and Configuration Guide

Optional guide to setting up Celery for background tasks. Celery is **completely optional** - the system automatically falls back to threading if Celery is not available. However, Celery is **recommended for production** as it provides better performance, monitoring, and task scheduling.

## Table of Contents

1. [When to Use Celery](#when-to-use-celery)
2. [Features](#features)
3. [Installation](#installation)
4. [Running Celery](#running-celery)
5. [Configuration](#configuration)
6. [Monitoring](#monitoring)
7. [Troubleshooting](#troubleshooting)
8. [Fallback to Threading](#fallback-to-threading)
9. [Best Practices](#best-practices)
10. [Additional Resources](#additional-resources)

---

## When to Use Celery

**Use Celery if:**
- ✅ You want scheduled tasks (daily scraping, etc.)
- ✅ You need better performance for background tasks
- ✅ You want task monitoring and management
- ✅ You're running in production

**You can skip Celery if:**
- ✅ You're just developing/testing
- ✅ You don't need scheduled tasks
- ✅ You prefer simpler setup (threading works fine)
- ✅ You don't want to run Redis

## Features

- ✅ **Optional**: Works without Celery (uses threading fallback)
- ✅ **Automatic Detection**: Detects if Celery is installed and configured
- ✅ **Cross-Platform**: Works on Windows, Linux, and macOS
- ✅ **Redis Backend**: Uses Redis as message broker and result backend
- ✅ **Scheduled Tasks**: Celery Beat for periodic scraping tasks

## Installation

### Prerequisites

1. **Redis** must be installed and running
2. **Python 3.11+** with virtual environment
3. **Celery** and related packages (optional)

### Step 1: Install Redis

#### Windows

**Option A: Using Memurai (Recommended)**
1. Download from: https://www.memurai.com/
2. Install and start the service
3. Redis will run on `localhost:6379` by default

**Option B: Using Docker**
```bash
docker run -d --name redis -p 6379:6379 redis
```

**Option C: Using WSL2**
```bash
# In WSL2 terminal
sudo apt-get update
sudo apt-get install redis-server
sudo service redis-server start
```

#### Linux (Ubuntu/Debian)

```bash
sudo apt-get update
sudo apt-get install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

#### macOS

```bash
brew install redis
brew services start redis
```

#### Verify Redis Installation

```bash
# Test Redis connection
redis-cli ping
# Should return: PONG

# Or using Python
python -c "import redis; r = redis.Redis(host='localhost', port=6379); r.ping(); print('Redis OK!')"
```

### Step 2: Install Celery (Optional)

Celery is **optional**. The project works without it, but you'll get better performance and scheduling with Celery.

```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install Celery and dependencies
pip install celery[redis] django-celery-beat django-redis
```

### Step 3: Configure Environment Variables

Edit your `.env` file:

```bash
# Enable Celery (default: True if Celery is installed)
ENABLE_CELERY=True

# Redis configuration (defaults shown)
CELERY_BROKER_URL=redis://localhost:6379
CELERY_RESULT_BACKEND=redis://localhost:6379
REDIS_URL=redis://localhost:6379/1
```

## Running Celery

### Option 1: Using Scripts (Recommended)

#### Windows

```bash
# Start Celery Worker
fkapi\start_celery_worker.bat

# Start Celery Beat (in another terminal)
fkapi\start_celery_beat.bat
```

#### Linux/Mac

```bash
# Make scripts executable (first time only)
chmod +x fkapi/start_celery_worker.sh
chmod +x fkapi/start_celery_beat.sh

# Start Celery Worker
./fkapi/start_celery_worker.sh

# Start Celery Beat (in another terminal)
./fkapi/start_celery_beat.sh
```

### Option 2: Manual Commands

#### Start Celery Worker

```bash
cd fkapi
python manage.py celery worker --loglevel=info --pool=threads --concurrency=4
```

Or using the Celery command directly:

```bash
cd fkapi
celery -A fkapi worker --loglevel=info --pool=threads --concurrency=4
```

#### Start Celery Beat (Scheduler)

```bash
cd fkapi
celery -A fkapi beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

### Option 3: Using Docker Compose

If you have a `docker-compose.yml` file:

```bash
# Start all services including Celery
docker-compose up -d

# Or start only Celery services
docker-compose up -d celery celerybeat

# View logs
docker-compose logs -f celery
docker-compose logs -f celerybeat
```

## Configuration

### Celery Settings

The Celery configuration is in `fkapi/fkapi/settings.py`:

```python
# Celery is optional - only configured if ENABLE_CELERY is True
ENABLE_CELERY = os.getenv('ENABLE_CELERY', 'True' if CELERY_AVAILABLE else 'False').lower() in ('1', 'true', 'yes')

if ENABLE_CELERY and CELERY_AVAILABLE:
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379')
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379')
    CELERY_BEAT_SCHEDULE = {
        'scrape_daily': {
            'task': 'core.tasks.scrape_daily',
            'schedule': crontab(hour=0, minute=0),  # Daily at midnight
        },
    }
```

### Scheduled Tasks

The default schedule runs `scrape_daily` every day at midnight. To change the schedule:

1. Edit `fkapi/fkapi/settings.py`
2. Modify `CELERY_BEAT_SCHEDULE`
3. Restart Celery Beat

Example schedules:

```python
# Daily at 3 AM
'schedule': crontab(hour=3, minute=0)

# Every 6 hours
'schedule': crontab(minute=0, hour='*/6')

# Weekly on Monday at 3 AM
'schedule': crontab(day_of_week=1, hour=3, minute=0)

# Every 30 minutes
'schedule': crontab(minute='*/30')
```

## Monitoring

### Flower (Web-based Monitoring)

Flower is a web-based tool for monitoring Celery clusters.

**Installation:**
```bash
pip install flower
```

**Start Flower:**
```bash
cd fkapi
celery -A fkapi flower --port=5555
```

**Access Dashboard:**
- Open browser: http://localhost:5555
- Monitor tasks, workers, and performance

### Command Line Monitoring

```bash
# Check active workers
celery -A fkapi inspect active

# Check registered tasks
celery -A fkapi inspect registered

# Check worker stats
celery -A fkapi inspect stats

# Monitor events in real-time
celery -A fkapi events
```

## Troubleshooting

### Issue: "Redis is not running"

**Solution:**
```bash
# Check if Redis is running
redis-cli ping

# Start Redis
# Windows: Start Memurai service
# Linux: sudo systemctl start redis-server
# Mac: brew services start redis
# Docker: docker start redis
```

### Issue: "ModuleNotFoundError: No module named 'celery'"

**Solution:**
```bash
# Install Celery
pip install celery[redis] django-celery-beat

# Or disable Celery
# Set ENABLE_CELERY=False in .env
```

### Issue: "Connection refused" to Redis

**Solution:**
1. Check Redis is running: `redis-cli ping`
2. Check Redis port (default: 6379)
3. Verify `CELERY_BROKER_URL` in `.env`
4. Check firewall settings

### Issue: Tasks not executing

**Solution:**
1. Verify Celery worker is running: `celery -A fkapi inspect active`
2. Check Celery Beat is running (for scheduled tasks)
3. Check logs for errors: `tail -f logs/celery.log`
4. Verify task is registered: `celery -A fkapi inspect registered`

### Issue: Tasks running but not completing

**Solution:**
1. Check worker logs for errors
2. Verify database connection
3. Check for deadlocks or long-running operations
4. Increase worker timeout if needed

## Fallback to Threading

If Celery is not available or disabled, the system automatically uses Python's `threading` module:

- Tasks execute in background threads
- No Redis required
- No separate worker process needed
- Suitable for development and small deployments

The fallback is automatic - no configuration needed.

## Best Practices

1. **Development**: Use threading fallback (no Celery needed)
2. **Production**: Use Celery with Redis for better performance
3. **Monitoring**: Use Flower for production monitoring
4. **Scaling**: Run multiple workers for high load
5. **Error Handling**: Tasks should handle errors gracefully
6. **Logging**: All tasks should log their progress

## Additional Resources

- [Celery Documentation](https://docs.celeryq.dev/)
- [Redis Documentation](https://redis.io/docs/)
- [Django Celery Beat](https://django-celery-beat.readthedocs.io/)
- [Flower Documentation](https://flower.readthedocs.io/)

## Quick Reference

### Start Services

```bash
# Windows
start_celery_worker.bat
start_celery_beat.bat

# Linux/Mac
./start_celery_worker.sh
./start_celery_beat.sh
```

### Check Status

```bash
# Redis
redis-cli ping

# Celery Worker
celery -A fkapi inspect active

# Celery Beat
ps aux | grep celerybeat
```

### View Logs

```bash
# Celery logs
tail -f logs/celery.log

# Django logs
tail -f logs/django.log
```

---

**Last Updated**: 2026-01-17
**Maintained by**: sunr4y
