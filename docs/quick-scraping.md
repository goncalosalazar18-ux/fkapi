# Quick Scraping Reference

Quick reference guide for common scraping tasks and workflows.

## Quick Start: Scrape Latest Kits Daily

### Setup (One-time)

```bash
# 1. Ensure .env is configured
cat .env | grep SCRAPER_USER_AGENT
# Should show your bot identification

# 2. Start Celery services
docker-compose up -d celery celerybeat

# 3. Check it's running
docker-compose ps celery
docker-compose ps celerybeat
```

### Daily Automated Scraping (Already configured)

The project already has daily scraping set up to run at midnight:

**What happens automatically:**
- Scrapes latest updated kits (first 5 pages)
- Uses proper delays (2-5 seconds between requests)
- Respects rate limits
- Logs all activity

**Manual test:**
```bash
# Test the daily scrape manually
docker-compose exec web python manage.py scrape_latest --pages 3

# Check logs
docker-compose logs web | grep -i scrape
```

**Monitor:**
```bash
# Check scraper logs
tail -f logs/scraper.log

# View Celery tasks in Flower
# Visit: http://localhost:5555
```

---

## Complete Site Scraping (First-Time)

### Ethical Scraping Workflow

**IMPORTANT**: Only scrape if you have permission from FootballKitArchive!

```bash
# STEP 1: Check robots.txt
curl https://www.footballkitarchive.com/robots.txt

# STEP 2: Configure delays
# Edit .env:
# HTTP_TIMEOUT=15
# HTTP_MAX_RETRIES=3
# HTTP_BACKOFF_FACTOR=0.5
# SCRAPER_USER_AGENT="FootballKitArchiveBot/1.0 (contact@youremail.com)"

# STEP 3: Test single club first
docker-compose exec web python manage.py scrape_whole_club --club-slug "arsenal-kits"

# STEP 4: If successful, proceed gradually
# Week 1: Top 50 clubs
# Week 2-8: Remaining clubs (10-20 per week)
```

### Recommended Schedule

**Week 1** (Top Clubs):
```bash
# Scrape 10 clubs per day
for day in {1..7}; do
    # Each day, scrape 10 different clubs
    python manage.py scrape_whole_club --club-slug "club1-kits"
    python manage.py scrape_whole_club --club-slug "club2-kits"
    # ... up to 10 clubs
    
    # Wait 1 day before next batch
    sleep 86400
done
```

**Week 2-8** (Remaining Clubs):
```bash
# Continue with 15-20 clubs per week
# Always wait between club scrapes
# Each club scrape has internal delays for individual kits
```

---

## Update Kit Photos

### Scenario: Leaked → Official Photos

**Identify kits to update:**
```bash
# Find kits with unofficial/leaked images
# (You'd need to mark these in your database)
# Look for image patterns or flags
```

**Update individual kit:**
```bash
# Update specific kit
docker-compose exec web python manage.py rescrape_kits --slug "arsenal-2024-home-1-kit"
```

**Update by season:**
```bash
# Update all kits for current season
docker-compose exec web python manage.py update_last_season --season "2024-25"
```

**Update from CSV list:**
```bash
# Create CSV with kits to update
cat > update_photos.csv << EOF
slug
arsenal-2024-home-1-kit
manchester-united-2024-away-kit
liverpool-2024-third-kit
EOF

# Update in batches of 10 at a time
docker-compose exec web python manage.py rescrape_kits --input update_photos.csv --batch-size 10
```

### Best Practices

1. **Check if image changed before updating**
   ```bash
   # The rescrape command should:
   # - Fetch new image URL
   # - Compare with current URL
   # - Only update if different
   ```

2. **Backup before mass updates**
   ```bash
   # Backup database before bulk updates
   python manage.py dbbackup
   ```

3. **Update in small batches**
   ```bash
   # Don't update all at once
   # Do 10-20 at a time
   # Wait between batches
   ```

---

## 🔄 Complete Scraping Command Reference

### Club-Level Scraping

```bash
# Scrape all kits for one club
python manage.py scrape_whole_club --club-slug "arsenal-kits"

# Scrape club details only
python manage.py scrape_club_details --club-slug "arsenal-kits"
```

### Kit-Level Scraping

```bash
# Scrape a specific kit by slug
python manage.py scrape_kit_by_slug --slug "arsenal-2024-home-1-kit"

# Rescrape existing kits (update data)
python manage.py rescrape_kits --slug "arsenal-2024-home-1-kit"
```

### Latest/Recent Kits

```bash
# Scrape latest pages (default: 5 pages)
python manage.py scrape_latest --pages 5

# Scrape with custom delay range
python manage.py scrape_latest --delay-min 2 --delay-max 5
```

### Brand Scraping

```bash
# Scrape brand information
python manage.py scrape_brand --brand-slug "adidas-kits"
```

### Data Updates

```bash
# Update season data
python manage.py update_last_season --season "2024-25"

# Update kit designs
python manage.py update_designs

# Update kit colors
python manage.py update_colors
```

---

## ⏰ Automated Scraping Schedule

### Current Setup (Daily)

```bash
# Runs every day at midnight (00:00)
# Scrapes: Latest pages 1-5
# Command: scrape_latest --pages 5
```

**Verify it's working:**
```bash
# Check Celery Beat is running
docker-compose ps celerybeat

# Check last run
tail -f logs/scraper.log | grep "scrape_daily"

# Check in Flower
# Visit: http://localhost:5555
# Look for task: "core.tasks.scrape_daily"
```

### Change Schedule

**Edit `fkapi/fkapi/settings.py`:**

```python
# Current: Daily at midnight
CELERY_BEAT_SCHEDULE = {
    'scrape_daily': {
        'task': 'core.tasks.scrape_daily',
        'schedule': crontab(hour=0, minute=0),
    },
}

# Change to: Daily at 3 AM (off-peak)
CELERY_BEAT_SCHEDULE = {
    'scrape_daily': {
        'task': 'core.tasks.scrape_daily',
        'schedule': crontab(hour=3, minute=0),
    },
}

# Change to: Weekly (every Monday at 3 AM)
CELERY_BEAT_SCHEDULE = {
    'scrape_weekly': {
        'task': 'core.tasks.scrape_daily',
        'schedule': crontab(day_of_week=1, hour=3, minute=0),
    },
}
```

**Restart Celery Beat after changes:**
```bash
docker-compose restart celerybeat
```

---

## 📊 Monitoring Scraping

### Real-time Monitoring

```bash
# View scraper logs
tail -f logs/scraper.log

# View Celery logs
tail -f logs/celery.log

# View all Docker logs
docker-compose logs -f
```

### Flower Dashboard

```bash
# Start Flower (if not running)
docker-compose up -d flower

# Access dashboard
# Visit: http://localhost:5555

# What to check:
# - Tasks tab: See task execution history
# - Workers tab: Check worker status
# - Monitor tab: Real-time task monitoring
# - Success rate: Should be >95%
# - Execution time: Average should be <5 minutes
```

### Health Checks

```bash
# API health check
curl http://localhost:8000/api/health

# Database connection
docker-compose exec web python manage.py dbshell

# Redis connection
docker-compose exec redis redis-cli ping
```

---

## ⚠️ Troubleshooting

### Too Many Requests (429 Errors)

```bash
# Increase delays
# Edit .env:
HTTP_BACKOFF_FACTOR=1.0  # Increase from 0.5

# Add delay between club scrapes
sleep 60  # Wait 60 seconds between clubs
```

### Scraping Too Slow

```bash
# Slightly decrease delays (but not below 1 second)
# Minimum recommended: 1 second between requests
```

### Scraping Fails Intermittently

```bash
# Check if site is up
curl https://www.footballkitarchive.com

# Check logs for specific errors
tail -f logs/scraper.log | grep ERROR
```

### Database Locks

```bash
# Too many concurrent writes
# Reduce Celery worker concurrency
# Edit docker-compose.yml:
# command: celery -A fkapi worker --loglevel=info --concurrency=1
```

---

## ✅ Scraping Checklist

### Before First Scrape

- [ ] Reviewed robots.txt for FootballKitArchive
- [ ] Reviewed Terms of Service
- [ ] Configured proper User-Agent in .env
- [ ] Set appropriate delays (2-5 seconds recommended)
- [ ] Tested single kit scrape successfully
- [ ] Monitoring is configured (logs, Flower)
- [ ] Database is backed up

### During Scraping

- [ ] Monitoring logs regularly
- [ ] Checking for 429 errors (rate limiting)
- [ ] Watching response times
- [ ] Not overloading server (delays working)
- [ ] Data quality being verified

### After Scraping

- [ ] Data quality checked (missing fields, duplicates)
- [ ] Images verified (not broken URLs)
- [ ] Database indexes updated
- [ ] Database backed up
- [ ] Any issues documented

---

## 🎯 Quick Reference

### Start All Services

```bash
# Start everything
docker-compose up -d

# Check status
docker-compose ps
```

### Test Scraping

```bash
# Test single kit
docker-compose exec web python manage.py scrape_kit_by_slug --slug "arsenal-2024-home-1-kit"

# Test latest scraping
docker-compose exec web python manage.py scrape_latest --pages 1
```

### Monitor Scraping

```bash
# Logs
tail -f logs/scraper.log

# Flower dashboard
# Visit: http://localhost:5555
```

### Stop Scraping

```bash
# Stop all services
docker-compose down

# Or stop just Celery
docker-compose stop celery celerybeat
```

---

## 📞 Quick Help

**Need more details?**
- See: [scraping-guide.md](scraping-guide.md) for comprehensive guide
- See: [README.md](../README.md) for project overview
- Check: [CONTRIBUTING.md](../CONTRIBUTING.md) for development workflow

**Issues?**
1. Check logs: `logs/scraper.log`
2. Check Flower: http://localhost:5555
3. Review [scraping-guide.md](scraping-guide.md) troubleshooting section

---

---

**Last Updated**: 2026-01-17  
**Maintained by**: sunr4y

**Remember**: Always scrape responsibly - respect robots.txt, use proper delays (2-5 seconds), don't overload servers, and monitor your scraping activity.
