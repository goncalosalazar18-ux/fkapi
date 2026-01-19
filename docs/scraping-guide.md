# Ethical Web Scraping Guide

Comprehensive guide to ethical web scraping practices, including robots.txt compliance, rate limiting, and legal considerations.

**IMPORTANT**: Always check FootballKitArchive's Terms of Service and robots.txt before scraping. This guide is educational and you must ensure you have permission to scrape any website.

## Table of Contents

1. [Legal and Ethical Considerations](#legal-and-ethical-considerations)
2. [Best Practices to Avoid DDOS](#best-practices-to-avoid-ddos)
3. [Implementation in This Project](#implementation-in-this-project)
4. [Monitoring and Logging](#monitoring-and-logging)
5. [Troubleshooting](#troubleshooting)
6. [Additional Resources](#additional-resources)

---

## Legal and Ethical Considerations

### 1. Check robots.txt

**Always check** the website's robots.txt file before scraping:

```bash
curl https://www.footballkitarchive.com/robots.txt
```

Example of what to look for:
```
User-agent: *
Disallow: /admin/
Disallow: /private/
Crawl-delay: 2
```

**Rules to follow:**
- Respect `Disallow` rules
- Honor `Crawl-delay` if specified
- Identify your bot with a proper User-Agent
- Provide contact information

### 2. Check Terms of Service

Review FootballKitArchive's Terms of Service for any scraping policies:
- Is scraping explicitly allowed?
- Are there rate limits mentioned?
- What is the allowed usage?
- Are there attribution requirements?

### 3. Fair Use Guidelines

Follow these fair use principles:
- **Only scrape what you need** - Don't download entire site unnecessarily
- **Cache responses** - Don't re-request the same data repeatedly
- **Respect copyright** - Don't use images for commercial purposes without permission
- **Give attribution** - Credit the source when displaying data
- **Don't overload servers** - Use reasonable delays between requests

---

## Best Practices to Avoid DDOS

### 1. Rate Limiting

Implement strict rate limiting:

```python
# Example: In your scraping code
import time

MIN_DELAY = 2  # Minimum 2 seconds between requests
MAX_DELAY = 5  # Maximum 5 seconds between requests
DELAY_RANGE = (MIN_DELAY, MAX_DELAY)

def scrape_with_delay(url):
    """Scrape URL with random delay."""
    response = requests.get(url)
    
    # Random delay between requests
    delay = random.uniform(*DELAY_RANGE)
    time.sleep(delay)
    
    return response
```

### 2. Use Delays in This Project

This project already has delay mechanisms configured:

**Environment Variables:**
```bash
# In .env
HTTP_TIMEOUT=15
HTTP_MAX_RETRIES=3
HTTP_BACKOFF_FACTOR=0.5
SCRAPER_USER_AGENT="YourBotName/1.0 (contact@youremail.com)"
```

**Configuration in scrapers:**
```python
# The scrapers.py file already has delays built-in
import random
import time

# Random delay between page requests
DELAY_MIN = 2
DELAY_MAX = 5
delay = random.uniform(DELAY_MIN, DELAY_MAX)
time.sleep(delay)
```

### 3. Implement Exponential Backoff

For failed requests, use exponential backoff:

```python
import time

def fetch_with_backoff(url, max_retries=3):
    """Fetch URL with exponential backoff on failures."""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            return response
        except (requests.RequestException, ConnectionError) as e:
            if attempt < max_retries - 1:
                # Exponential backoff: 2^attempt seconds
                wait_time = (2 ** attempt) + random.random()
                time.sleep(wait_time)
                logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time:.2f}s")
            else:
                raise
```

### 4. Use Session with Connection Pooling

Reuse HTTP connections:

```python
import requests

# Configure session with connection pooling
session = requests.Session()
adapter = HTTPAdapter(
    max_retries=3,
    pool_connections=10,
    pool_maxsize=10
)
session.mount('https://', adapter)

# Use this session for all requests
response = session.get(url)
```

### 5. Respect HTTP Headers

Include proper headers:

```python
headers = {
    'User-Agent': 'YourBot/1.0 (contact@youremail.com)',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
}
```

---

## Complete Scraping Workflow

### Phase 1: Pre-Scraping Setup

1. **Check Permissions**
   ```bash
   # Check robots.txt
   curl https://www.footballkitarchive.com/robots.txt
   
   # Check Terms of Service
   # Visit: https://www.footballkitarchive.com/terms
   ```

2. **Configure Environment**
   ```bash
   # In .env file
   SCRAPER_USER_AGENT="FootballKitArchiveBot/1.0 (contact@youremail.com)"
   HTTP_TIMEOUT=15
   HTTP_MAX_RETRIES=3
   HTTP_BACKOFF_FACTOR=0.5
   
   # Optional: Use an HTTP proxy to distribute load (from any provider)
   # PROXY_URL=http://user:pass@proxy.example.com:8080/
   ```

3. **Test Single Request**
   ```bash
   # Test a single page first
   python manage.py scrape_kit_by_slug --slug "arsenal-2024-home-kit"
   ```

### Phase 2: Incremental Scraping

**Option 1: Scrape by Club (Recommended)**

Scrape one club at a time to distribute load:

```bash
# Scrape kits for a specific club
python manage.py scrape_whole_club --club-slug "arsenal-kits"

# This will:
# 1. Get list of all kits for the club
# 2. Scrape each kit with delays
# 3. Save to database
# 4. Continue even if some fail
```

**Recommended Schedule:**
```bash
# Week 1: Top 50 clubs
# Week 2: Next 50 clubs
# Week 3-8: Continue gradually
```

**Option 2: Scrape Latest Pages Only**

Scrape only recently updated kits:

```bash
# Scrape latest updated kits (pages 1-5)
python manage.py scrape_latest --pages 5

# This scrapes:
# - Only the "Latest Kits" pages
# - Most recently updated/added kits
# - With proper delays between requests
```

**Option 3: Scrape Individual Kits (For Specific Updates)**

```bash
# Scrape a specific kit by slug
python manage.py scrape_kit_by_slug --slug "manchester-united-2024-home-1-kit"
```

### Phase 3: Monitor and Adjust

1. **Monitor Logs**
   ```bash
   # Check scraper logs for errors
   tail -f logs/scraper.log
   
   # Look for:
   # - 429 Too Many Requests (reduce rate)
   # - 500/502/503 errors (server issues)
   # - 404 errors (page not found)
   ```

2. **Check Response Times**
   ```bash
   # If responses are slow (>5 seconds), increase delays
   # If responses are fast, you can slightly decrease
   ```

3. **Adjust Rate Limiting**
   ```bash
   # In .env, adjust delays
   # If getting 429 errors:
   DELAY_MIN=3  # Increase from 2
   DELAY_MAX=8  # Increase from 5
   ```

---

## Daily Automated Scraping

This project already has automated daily scraping configured:

### Current Setup

**Celery Task** (`fkapi/core/tasks.py`):
```python
from celery import shared_task
from django.core.management import call_command

@shared_task
def scrape_daily():
    """Scrape latest updated kits once a day using django command called scrape_latest"""
    call_command('scrape_latest')
```

**Celery Beat Schedule** (`fkapi/fkapi/settings.py`):
```python
CELERY_BEAT_SCHEDULE = {
    'scrape_daily': {
        'task': 'core.tasks.scrape_daily',
        'schedule': crontab(hour=0, minute=0),  # Daily at midnight
    },
}
```

### How to Enable

1. **Ensure Celery Beat is Running**

```bash
# Option 1: Docker
docker-compose up -d celerybeat

# Option 2: Local
cd fkapi
celery -A fkapi beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

2. **Configure Daily Scrape Limits**

Edit the daily scrape to limit pages:

```python
# In fkapi/core/tasks.py, modify to add pages limit
@shared_task
def scrape_daily():
    """Scrape latest updated kits once a day, limited to first 5 pages."""
    # Limit to first 5 pages to avoid overloading
    call_command('scrape_latest', '--pages', '5')
```

3. **Monitor Daily Scrapes**

```bash
# Check logs
tail -f logs/scraper.log

# Check Celery Beat logs
tail -f logs/celerybeat.log

# View in Flower (if running)
# Visit: http://localhost:5555
# Click on "Tasks" tab
# Filter by task name: "core.tasks.scrape_daily"
```

### Best Practices for Daily Scraping

1. **Scrape at Off-Peak Hours**
   ```python
   # Scrape at 3 AM server time (low traffic)
   CELERY_BEAT_SCHEDULE = {
       'scrape_daily': {
           'task': 'core.tasks.scrape_daily',
           'schedule': crontab(hour=3, minute=0),  # 3 AM
       },
   }
   ```

2. **Limit Pages Per Day**
   ```bash
   # Only scrape first 3-5 pages daily
   python manage.py scrape_latest --pages 3
   ```

3. **Stop When No New Items**

The `scrape_latest` command should detect when there are no new items:

```python
# The existing command should check if new items were found
# If 0 new items on consecutive days, reduce frequency

# Example enhancement:
if new_kits_count == 0:
    consecutive_empty_days += 1
    if consecutive_empty_days >= 7:
        # No new items for a week, reduce to weekly
        # Change schedule to weekly
        pass
else:
    consecutive_empty_days = 0
```

---

## Updating Kit Photos

### Scenario: Leaked vs. Official Photos

Sometimes kits are initially posted with leaked/placeholder images and later updated with official photos. Here's how to update them:

### Method 1: Rescrape Specific Kits

```bash
# Update photos for specific kit
python manage.py rescrape_kits --slug "arsenal-2024-home-1-kit"

# This will:
# 1. Re-fetch the kit page
# 2. Check if image URL has changed
# 3. Update if different
```

### Method 2: Update by Season

Update all kits for a specific season:

```bash
# Update all kits for 2024-25 season
python manage.py update_last_season --season "2024-25"

# This will:
# 1. Find all kits for the season
# 2. Re-scrape each kit
# 3. Update images if changed
# 4. Use proper delays between requests
```

### Method 3: Bulk Update from CSV

Create a CSV of kits to update and use existing commands:

```bash
# Create CSV with kit slugs
echo "slug" > kits_to_update.csv
echo "arsenal-2024-home-1-kit" >> kits_to_update.csv
echo "manchester-united-2024-away-kit" >> kits_to_update.csv

# Use existing rescrape command
python manage.py rescrape_kits --input kits_to_update.csv
```

### Best Practices for Photo Updates

1. **Check Image Hash Before Updating**
   ```python
   # Don't update if image hasn't changed
   # Compute hash of current image
   # Compare with new image
   # Only update if different
   ```

2. **Backup Old Images**
   ```python
   # Keep backup of old images
   # Don't delete immediately
   # Allow rollback if needed
   ```

3. **Update in Batches**
   ```bash
   # Update 100 kits at a time
   # Wait between batches
   # Monitor for errors
   ```

---

## Monitoring Scraping Health

### 1. Track Success Rates

```python
# Log success/failure rates
# Monitor in logs
# Alert if failure rate > 10%
```

### 2. Track Response Times

```python
# Log response times for each request
# Alert if average > 5 seconds
# Adjust delays accordingly
```

### 3. Track Data Quality

```python
# Check for incomplete data
# Flag kits missing key fields
# Manually review flagged kits
```

### 4. Use Flower for Monitoring

```bash
# Start Flower
celery -A fkapi flower --port=5555

# Visit http://localhost:5555
# Monitor:
# - Task success/failure rates
# - Task execution times
# - Worker performance
```

---

## Common Mistakes to Avoid

### 1. Scraping Too Fast

**❌ Don't:**
```python
# Scrape 1000 pages without delays
for page in range(1000):
    scrape_page(page)
```

**✅ Do:**
```python
# Add delays between requests
for page in range(1000):
    scrape_page(page)
    time.sleep(random.uniform(2, 5))  # 2-5 second delay
```

### 2. Not Handling Errors

**❌ Don't:**
```python
# Let exceptions crash the scraper
response = requests.get(url)
```

**✅ Do:**
```python
# Handle errors gracefully
try:
    response = requests.get(url, timeout=15)
    response.raise_for_status()
except requests.RequestException as e:
    logger.error(f"Failed to scrape {url}: {e}")
    return None
```

### 3. Scraping Unnecessary Data

**❌ Don't:**
```python
# Scrape the entire site every day
scrape_entire_site()
```

**✅ Do:**
```python
# Only scrape latest updates
scrape_latest_pages(limit=5)
```

### 4. Not Respecting Robots.txt

**❌ Don't:**
```python
# Scrape disallowed pages
scrape_page('/admin/')
scrape_page('/private/')
```

**✅ Do:**
```python
# Check robots.txt first
if path_is_allowed(path):
    scrape_page(path)
```

---

## Recommended Scraping Schedule

### For Initial Population (First Time)

**Week 1-2: Top Clubs**
- Scrape top 50 clubs (highest traffic)
- 5-10 clubs per day
- 20-50 kits per day

**Week 3-8: Remaining Clubs**
- Scrape remaining clubs gradually
- 10-20 clubs per day
- 50-100 kits per day

**Total Time**: 8 weeks to scrape ~5,000 clubs (300,000+ kits)

### For Ongoing Updates (After Initial)

**Daily:**
- Scrape latest pages (3-5 pages)
- 50-100 new/updated kits per day
- Runs at 3 AM server time

**Weekly:**
- Rescrape specific clubs for photo updates
- 1-2 clubs per week
- 10-20 kits per week

**Monthly:**
- Review and fix data quality issues
- Check for broken images
- Update season data

---

## Troubleshooting

### Issue: 429 Too Many Requests

**Solution:**
```bash
# Increase delays in .env
DELAY_MIN=5  # Increase from 2
DELAY_MAX=10  # Increase from 5

# Add proxy if needed (generic HTTP proxy provider)
PROXY_URL=http://user:pass@proxy.example.com:8080/
```

### Issue: 500/502/503 Errors

**Solution:**
```bash
# Check if site is down
curl https://www.footballkitarchive.com

# Add retry logic with exponential backoff
# (already configured in http.py)
```

### Issue: 404 Not Found

**Solution:**
```bash
# Kit page was moved or deleted
# Log the error
# Mark kit as "deleted" or "needs_review"
```

### Issue: Slow Scraping

**Solution:**
```bash
# If too slow, can slightly reduce delays
# But don't go below 1 second
DELAY_MIN=1  # Don't go lower than this
DELAY_MAX=3
```

---

## Scraping Checklist

Before Scraping:

- [ ] Reviewed robots.txt
- [ ] Reviewed Terms of Service
- [ ] Configured proper User-Agent
- [ ] Set appropriate delays (2-5 seconds)
- [ ] Tested single request successfully
- [ ] Monitoring is configured
- [ ] Error handling is in place
- [ ] Logs are being captured

During Scraping:

- [ ] Monitoring logs regularly
- [ ] Checking for 429 errors
- [ ] Watching response times
- [ ] Verifying data quality
- [ ] Not overloading server

After Scraping:

- [ ] Verified data quality
- [ ] Checked for duplicates
- [ ] Updated database indexes
- [ ] Backed up database
- [ ] Documented any issues

---

## Additional Resources

- [robots.txt Checker](https://robotstxt.com/)
- [Python requests documentation](https://docs.python-requests.org/)
- [Scraping best practices](https://www.scrape.center/)
- [Rate limiting in Python](https://blog.devops.dev/rate-limiting-in-python/)

---

## Support

If you encounter issues:
1. Check logs in `logs/scraper.log`
2. Review this guide for common issues
3. Check Celery Beat logs for task failures
4. Review Flower for task monitoring

---

---

**Last Updated**: 2026-01-17  
**Maintained by**: sunr4y

**Remember**: Always scrape responsibly and legally!
