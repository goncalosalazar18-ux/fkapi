# Deployment Guide

This guide covers deploying the Football Kit Archive API to production.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Configuration](#environment-configuration)
3. [Database Setup](#database-setup)
4. [Redis Setup](#redis-setup)
5. [Application Deployment](#application-deployment)
6. [Celery Setup](#celery-setup)
7. [Static Files](#static-files)
8. [Monitoring and Logging](#monitoring-and-logging)
9. [Performance Optimization](#performance-optimization)
10. [Security Hardening](#security-hardening)

## Prerequisites

### Production Server Requirements

- **OS**: Ubuntu 22.04 LTS or later (recommended)
- **Python**: 3.11 or later
- **PostgreSQL**: 15 or later
- **Redis**: 7 or later
- **RAM**: Minimum 2GB (4GB+ recommended)
- **Storage**: Minimum 20GB (50GB+ recommended for growth)

### Software Required

```bash
# System dependencies
sudo apt-get update
sudo apt-get install -y \
    python3.11 \
    python3-pip \
    python3-venv \
    postgresql-15 \
    postgresql-contrib \
    redis-server \
    nginx \
    git \
    supervisor
```

## Environment Configuration

### 1. Create Environment File

```bash
# Copy environment template
cp .env.example .env
```

### 2. Configure Production Variables

Edit `.env` with production values:

```bash
# Django Settings
DJANGO_SECRET_KEY=<generate-strong-secret-key>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DJANGO_LOG_LEVEL=WARNING

# Database Settings
POSTGRES_DB=fkapi_prod
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<strong-password>
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
CONN_MAX_AGE=60

# Redis Settings
REDIS_URL=redis://localhost:6379/1
USE_REDIS_CACHE=True

# Scraper Settings
SCRAPER_REUSE_SESSION=True
SCRAPER_USER_AGENT="Mozilla/5.0 (compatible; FootballKitArchiveBot/1.0; +https://yourdomain.com/bot)"
HTTP_TIMEOUT=15
HTTP_MAX_RETRIES=3
HTTP_BACKOFF_FACTOR=0.5

# API Settings
DJANGO_API_ENABLE_AUTH=True

# Sentry Settings
SENTRY_DSN=your-sentry-dsn
SENTRY_TRACES_SAMPLE_RATE=0.1
SENTRY_ENVIRONMENT=production

# Security Settings
SECURE_HSTS_SECONDS=31536000
SECURE_SSL_REDIRECT=True
TRUST_X_FORWARDED_FOR=True
```

### 3. Generate Secret Key

```bash
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## Database Setup

### 1. Create PostgreSQL Database

```bash
# Access PostgreSQL
sudo -u postgres psql

# Run SQL commands
CREATE DATABASE fkapi_prod;
CREATE USER fkapi_user WITH PASSWORD 'strong_password';
GRANT ALL PRIVILEGES ON DATABASE fkapi_prod TO fkapi_user;
ALTER USER fkapi_user WITH SUPERUSER;
\q
```

### 2. Configure PostgreSQL for Performance

Edit `/etc/postgresql/15/main/postgresql.conf`:

```ini
# Memory settings (adjust based on available RAM)
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100

# Connection settings
max_connections = 100

# Query tuning
random_page_cost = 1.1
effective_io_concurrency = 200
```

Restart PostgreSQL:
```bash
sudo systemctl restart postgresql
```

### 3. Setup Automated Backups

Create backup script `/usr/local/bin/backup_db.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/var/backups/fkapi"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="fkapi_prod"

mkdir -p $BACKUP_DIR

pg_dump $DB_NAME | gzip > "$BACKUP_DIR/backup_$DATE.sql.gz"

# Keep only last 30 days of backups
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +30 -delete
```

Make executable:
```bash
sudo chmod +x /usr/local/bin/backup_db.sh
```

Add to crontab:
```bash
sudo crontab -e
```

Add line for daily backups at 2 AM:
```
0 2 * * * /usr/local/bin/backup_db.sh
```

## Redis Setup

### 1. Configure Redis for Production

Edit `/etc/redis/redis.conf`:

```ini
# Security
bind 127.0.0.1 ::1
protected-mode yes
requirepass <redis-password>

# Persistence
save 900 1
save 300 10
save 60 10000

# Memory management
maxmemory 256mb
maxmemory-policy allkeys-lru
```

Restart Redis:
```bash
sudo systemctl restart redis-server
```

### 2. Update Environment with Redis Password

```bash
# Update .env
REDIS_URL=redis://:<redis-password>@localhost:6379/1
```

## Application Deployment

### Option 1: Using Docker (Recommended)

#### 1. Clone Repository

```bash
cd /opt
sudo git clone <your-repo-url> fkapi
cd fkapi
```

#### 2. Build Docker Images

```bash
sudo docker-compose build
```

#### 3. Start Services

```bash
sudo docker-compose up -d
```

#### 4. Run Migrations

```bash
sudo docker-compose exec web python manage.py migrate --noinput
```

#### 5. Create Superuser

```bash
sudo docker-compose exec web python manage.py createsuperuser
```

#### 6. Collect Static Files

```bash
sudo docker-compose exec web python manage.py collectstatic --noinput
```

### Option 2: Traditional Deployment

#### 1. Create User and Directory

```bash
# Create deployment user
sudo adduser fkapi
sudo usermod -aG sudo fkapi

# Create application directory
sudo mkdir -p /var/www/fkapi
sudo chown fkapi:fkapi /var/www/fkapi
```

#### 2. Clone Repository

```bash
cd /var/www/fkapi
sudo -u fkapi git clone <your-repo-url> .
```

#### 3. Setup Virtual Environment

```bash
cd /var/www/fkapi
sudo -u fkapi python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

#### 4. Run Migrations

```bash
cd fkapi
python manage.py migrate --noinput
```

#### 5. Collect Static Files

```bash
python manage.py collectstatic --noinput
```

#### 6. Configure Gunicorn

Install Gunicorn:
```bash
pip install gunicorn
```

Create Gunicorn systemd service file `/etc/systemd/system/fkapi.service`:

```ini
[Unit]
Description=Fkapi Gunicorn Service
After=network.target postgresql.service redis.service

[Service]
User=fkapi
Group=fkapi
WorkingDirectory=/var/www/fkapi/fkapi
Environment="PATH=/var/www/fkapi/venv/bin"
ExecStart=/var/www/fkapi/venv/bin/gunicorn \
    --workers 3 \
    --bind unix:/var/www/fkapi/fkapi.sock \
    --access-logfile /var/www/fkapi/logs/gunicorn-access.log \
    --error-logfile /var/www/fkapi/logs/gunicorn-error.log \
    --log-level info \
    --capture-output \
    --timeout 120 \
    fkapi.wsgi:application

[Install]
WantedBy=multi-user.target
```

Enable and start service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable fkapi
sudo systemctl start fkapi
sudo systemctl status fkapi
```

## Celery Setup

### Configure Celery Worker

Create Celery worker systemd service `/etc/systemd/system/fkapi-celery.service`:

```ini
[Unit]
Description=Celery Worker for Fkapi
After=network.target redis.service postgresql.service

[Service]
Type=forking
User=fkapi
Group=fkapi
WorkingDirectory=/var/www/fkapi/fkapi
Environment="PATH=/var/www/fkapi/venv/bin"
ExecStart=/var/www/fkapi/venv/bin/celery -A fkapi worker \
    --loglevel=info \
    --logfile=/var/www/fkapi/logs/celery.log \
    --pidfile=/var/www/fkapi/celery.pid \
    --concurrency=2
ExecStop=/var/www/fkapi/venv/bin/celery -A fkapi multi stopwait \
    --pidfile=/var/www/fkapi/celery.pid

[Install]
WantedBy=multi-user.target
```

### Configure Celery Beat

Create Celery beat systemd service `/etc/systemd/system/fkapi-celerybeat.service`:

```ini
[Unit]
Description=Celery Beat for Fkapi
After=network.target redis.service postgresql.service

[Service]
Type=forking
User=fkapi
Group=fkapi
WorkingDirectory=/var/www/fkapi/fkapi
Environment="PATH=/var/www/fkapi/venv/bin"
ExecStart=/var/www/fkapi/venv/bin/celery -A fkapi beat \
    --loglevel=info \
    --logfile=/var/www/fkapi/logs/celerybeat.log \
    --pidfile=/var/www/fkapi/celerybeat.pid \
    --scheduler django_celery_beat.schedulers:DatabaseScheduler
ExecStop=/var/www/fkapi/venv/bin/celery -A fkapi multi stopwait \
    --pidfile=/var/www/fkapi/celerybeat.pid

[Install]
WantedBy=multi-user.target
```

Enable services:
```bash
sudo systemctl daemon-reload
sudo systemctl enable fkapi-celery fkapi-celerybeat
sudo systemctl start fkapi-celery fkapi-celerybeat
```

## Static Files

### 1. Configure Nginx

Create Nginx configuration `/etc/nginx/sites-available/fkapi`:

```nginx
upstream fkapi_server {
    server unix:/var/www/fkapi/fkapi.sock fail_timeout=0;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL Configuration (certbot will configure this)
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Client body size limit
    client_max_body_size 20M;

    # Static files
    location /static/ {
        alias /var/www/fkapi/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Media files
    location /media/ {
        alias /var/www/fkapi/media/;
        expires 7d;
    }

    # API endpoints
    location /api/ {
        proxy_pass http://fkapi_server;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        proxy_connect_timeout 120s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
    }

    # Health check
    location /health/ {
        proxy_pass http://fkapi_server;
        access_log off;
    }

    # Admin interface
    location /admin/ {
        proxy_pass http://fkapi_server;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 2. Enable Site

```bash
sudo ln -s /etc/nginx/sites-available/fkapi /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 3. Obtain SSL Certificate

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal
sudo certbot renew --dry-run
```

## Monitoring and Logging

### 1. Setup Log Rotation

Create logrotate config `/etc/logrotate.d/fkapi`:

```
/var/www/fkapi/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 fkapi fkapi
    sharedscripts
    postrotate
        systemctl reload fkapi
        systemctl reload fkapi-celery
    endscript
}
```

### 2. Setup Monitoring

#### Install Flower (Celery Monitoring)

```bash
pip install flower
```

Create Flower systemd service `/etc/systemd/system/fkapi-flower.service`:

```ini
[Unit]
Description=Flower for Celery
After=network.target redis.service

[Service]
User=fkapi
Group=fkapi
WorkingDirectory=/var/www/fkapi/fkapi
Environment="PATH=/var/www/fkapi/venv/bin"
ExecStart=/var/www/fkapi/venv/bin/celery -A fkapi flower \
    --port=5555 \
    --url_prefix=flower

[Install]
WantedBy=multi-user.target
```

Add to Nginx config:

```nginx
location /flower/ {
    proxy_pass http://127.0.0.1:5555/;
    # Add authentication here if needed
}
```

#### Configure Sentry

Ensure `SENTRY_DSN` is set in `.env` file for automatic error tracking.

### 3. Setup Uptime Monitoring

Consider using external monitoring services:
- UptimeRobot (free)
- Pingdom
- StatusCake

## Performance Optimization

### 1. Database Indexing

Review and add indexes as needed:
```python
# Example: Add index for kit searches
from django.db import models

class Kit(models.Model):
    # ... existing fields ...
    
    class Meta:
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['slug']),
            models.Index(fields=['team']),
            models.Index(fields=['season']),
        ]
```

### 2. Cache Configuration

Enable Django cache backend:
```python
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.getenv('REDIS_URL'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {'max_connections': 50}
        },
        'KEY_PREFIX': 'fkapi',
        'TIMEOUT': 300,
    }
}
```

### 3. Connection Pooling

Ensure database connection pooling is configured:
```python
DATABASES = {
    'default': {
        # ... existing config ...
        'CONN_MAX_AGE': 60,
        'OPTIONS': {
            'keepalives': 1,
            'keepalives_idle': 30,
            'keepalives_interval': 10,
            'keepalives_count': 5,
        }
    }
}
```

### 4. Enable Gzip Compression

Add to Nginx config:
```nginx
gzip on;
gzip_vary on;
gzip_proxied any;
gzip_comp_level 6;
gzip_types text/plain text/css text/xml application/json application/javascript application/xml+rss;
```

## Security Hardening

### 1. Firewall Configuration

```bash
# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable
sudo ufw status
```

### 2. Fail2Ban Installation

```bash
sudo apt-get install fail2ban

# Configure Fail2Ban for Nginx
sudo nano /etc/fail2ban/jail.local
```

### 3. Regular Updates

Set up automatic security updates:
```bash
sudo apt-get install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

### 4. File Permissions

```bash
# Set proper permissions
sudo chown -R fkapi:www-data /var/www/fkapi
sudo chmod -R 750 /var/www/fkapi
sudo find /var/www/fkapi -type d -exec chmod 750 {} \;
sudo find /var/www/fkapi -type f -exec chmod 640 {} \;
```

## Troubleshooting

### Common Issues

**Application not starting:**
```bash
# Check logs
sudo journalctl -u fkapi -f
sudo journalctl -u fkapi-celery -f

# Check environment variables
cat .env
```

**Database connection issues:**
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Test connection
sudo -u postgres psql -d fkapi_prod
```

**Celery not processing tasks:**
```bash
# Check Celery status
sudo systemctl status fkapi-celery
sudo celery -A fkapi inspect active

# Check Flower
curl http://localhost:5555/
```

**Nginx 502 errors:**
```bash
# Check if Gunicorn is running
sudo systemctl status fkapi

# Check socket file
ls -la /var/www/fkapi/fkapi.sock

# Check Nginx error logs
sudo tail -f /var/log/nginx/error.log
```

## Maintenance

### Regular Maintenance Tasks

1. **Weekly:**
   - Check log files for errors
   - Review system resources
   - Check backup files

2. **Monthly:**
   - Update dependencies
   - Review security updates
   - Clean up old logs
   - Test backup restoration

3. **Quarterly:**
   - Full security audit
   - Performance review
   - Capacity planning
   - Update documentation

## Rollback Procedure

If deployment fails:

```bash
# 1. Stop services
sudo systemctl stop fkapi fkapi-celery

# 2. Restore from backup
pg_restore -d fkapi_prod /var/backups/fkapi/backup_<timestamp>.sql.gz

# 3. Revert code changes
cd /var/www/fkapi
git checkout <previous-commit>

# 4. Restart services
sudo systemctl start fkapi fkapi-celery
```

## Support

For deployment issues:
1. Check logs: `/var/www/fkapi/logs/`
2. Review documentation in `docs/` directory
3. Open issue on GitHub

---

---

**Last Updated**: 2026-01-17  
**Maintained by**: sunr4y
