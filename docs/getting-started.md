# Getting Started Guide

Complete setup guide from scratch, including initial database population and ethical scraping practices.

**Note**: This project works **without Celery**. Celery is optional and recommended for production, but the system automatically falls back to threading if Celery is not available.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Initial Data Population](#initial-data-population)
4. [Automated Daily Scraping](#automated-daily-scraping)
5. [Best Practices](#best-practices)
6. [Troubleshooting](#troubleshooting)
7. [Next Steps](#next-steps)
8. [Additional Resources](#additional-resources)

---

## Prerequisites

- Python 3.11+
- PostgreSQL 15+ (or SQLite for development)
- Redis 6+ (optional, for caching and Celery if you choose to use it)
- Git

## Initial Setup

### Step 1: Clone and Install

```bash
# Clone the repository
git clone <repository-url>
cd FKApi

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
# Minimum required:
# - Database credentials (POSTGRES_*)
# - Django secret key (DJANGO_SECRET_KEY)
# - Scraper user agent (SCRAPER_USER_AGENT)
```

### Step 3: Database Setup

```bash
# Create database (PostgreSQL)
createdb fkapi

# Or use Docker
docker run -d --name postgres \
  -e POSTGRES_DB=fkapi \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=yourpassword \
  -p 5432:5432 \
  postgres:15

# Run migrations
cd fkapi
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### Step 4: Verify Installation

```bash
# Start development server
python manage.py runserver

# In another terminal, test API
curl http://localhost:8000/api/health

# Access admin interface
# http://localhost:8000/admin
```

## Initial Data Population

**IMPORTANT**: The database starts empty. You need to populate it with data through ethical scraping.

### Before You Start Scraping

#### 1. Review robots.txt

**Always check the website's robots.txt before scraping:**

```bash
curl https://www.footballkitarchive.com/robots.txt
```

**What to look for:**
- `Disallow` rules (pages you cannot scrape)
- `Crawl-delay` (minimum time between requests)
- `User-agent` rules (specific rules for your bot)

**Rules to follow:**
- ✅ Respect all `Disallow` rules
- ✅ Honor `Crawl-delay` if specified (minimum 2 seconds recommended)
- ✅ Use a proper User-Agent header
- ✅ Include contact information in User-Agent

#### 2. Review Terms of Service

Visit the website's Terms of Service page and check:
- Is scraping explicitly allowed?
- Are there rate limits mentioned?
- What is the allowed usage?
- Are there attribution requirements?

#### 3. Configure Scraper Settings

Edit your `.env` file:

```bash
# Scraper identification (REQUIRED)
SCRAPER_USER_AGENT="FootballKitArchiveBot/1.0 (contact@youremail.com)"

# Rate limiting (REQUIRED)
HTTP_TIMEOUT=15
HTTP_MAX_RETRIES=3
HTTP_BACKOFF_FACTOR=0.5

# Delays between requests (REQUIRED - minimum 2 seconds)
DELAY_MIN=2
DELAY_MAX=5
```

### Ethical Scraping Workflow

#### Phase 1: Test Single Request

**Always test with a single request first:**

```bash
# Test scraping a single kit
python manage.py scrape_kit_by_slug --slug "arsenal-2024-home-kit"

# Verify:
# - Request was successful
# - Data was saved correctly
# - No errors in logs
# - Respectful delay was used
```

#### Phase 2: Scrape by Club (Recommended)

**Scrape one club at a time to distribute load:**

```bash
# Scrape all kits for a specific club
python manage.py scrape_whole_club --club-slug "arsenal-kits"

# This will:
# - Get list of all kits for the club
# - Scrape each kit with delays (2-5 seconds)
# - Save to database
# - Continue even if some fail
```

**Recommended Schedule for Initial Population:**

- **Week 1**: Top 50 clubs (5-10 clubs per day)
- **Week 2-4**: Next 100 clubs (10-15 clubs per week)
- **Week 5-8**: Remaining clubs (20-30 clubs per week)

**Total Time**: 8 weeks to scrape ~5,000 clubs (300,000+ kits)

#### Phase 3: Scrape Latest Pages (For Updates)

**After initial population, use this for daily updates:**

```bash
# Scrape latest updated kits (first 5 pages)
python manage.py scrape_latest --start-page 1 --end-page 5

# This scrapes:
# - Only the "Latest Kits" pages
# - Most recently updated/added kits
# - With proper delays between requests
# - Stops when all kits on a page already exist
```

### Automated Daily Scraping

Once your database is populated, you can set up automated daily scraping. The project supports multiple options:

#### Option 1: Using Celery (Recommended for Production)

Celery provides better performance and monitoring. See [celery-setup.md](celery-setup.md) for detailed instructions.

**Note**: Celery is **optional**. The system works without it using threading fallback.

#### Option 2: Using Cron (Linux/Mac)

```bash
# Edit crontab
crontab -e

# Add daily scraping at 3 AM
0 3 * * * cd /path/to/FKApi && source venv/bin/activate && cd fkapi && python manage.py scrape_latest --start-page 1 --end-page 5
```

#### Option 3: Using Task Scheduler (Windows)

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger: Daily at 3:00 AM
4. Set action: Run program
   - Program: `C:\path\to\venv\Scripts\python.exe`
   - Arguments: `fkapi\manage.py scrape_latest --start-page 1 --end-page 5`
   - Start in: `C:\path\to\FKApi\fkapi`

## Best Practices

### 1. Rate Limiting

**Always use delays between requests:**
- Minimum: 2 seconds between requests
- Recommended: 2-5 seconds (randomized)
- Maximum: Respect `Crawl-delay` from robots.txt

**The scraper already includes delays, but verify:**
```python
# In scrapers.py, delays are configured:
DELAY_MIN = 2  # seconds
DELAY_MAX = 5  # seconds
```

### 2. Error Handling

**The scraper handles errors gracefully:**
- Retries failed requests (with exponential backoff)
- Logs all errors for review
- Continues processing even if some items fail
- Respects HTTP status codes (429, 503, etc.)

### 3. Monitoring

**Monitor your scraping activity:**
```bash
# View scraper logs
tail -f logs/scraper.log

# Check for errors
grep ERROR logs/scraper.log

# Monitor database growth
python manage.py shell
>>> from core.models import Kit
>>> Kit.objects.count()
```

### 4. Data Quality

**Regularly check data quality:**
```bash
# Find kits with missing data
python manage.py shell
>>> from core.models import Kit
>>> Kit.objects.filter(main_img_url__isnull=True).count()

# Find duplicate kits
python manage.py find_duplicate_kits

# Check for broken images
python manage.py check_broken_images
```

## Troubleshooting

### Issue: Empty Database After Setup

**Solution:** This is normal! The database starts empty. You need to populate it through scraping:
1. Follow the "Initial Data Population" section above
2. Start with a single club: `python manage.py scrape_whole_club --club-slug "arsenal-kits"`
3. Gradually expand to more clubs

### Issue: 429 Too Many Requests

**Solution:** You're scraping too fast:
1. Increase delays in `.env`: `DELAY_MIN=5 DELAY_MAX=10`
2. Reduce concurrent requests
3. Add longer delays between club scrapes

### Issue: Scraping Too Slow

**Solution:**
1. Verify delays are not too high
2. Check network connection
3. Consider using proxy (if allowed by robots.txt)
4. Scrape during off-peak hours

### Issue: Database Connection Errors

**Solution:**
1. Verify PostgreSQL is running: `pg_isready`
2. Check database credentials in `.env`
3. Verify database exists: `psql -l | grep fkapi`
4. Test connection: `python manage.py dbshell`

## Next Steps

1. ✅ Complete initial setup
2. ✅ Review robots.txt and Terms of Service
3. ✅ Configure scraper settings
4. ✅ Test with single kit scrape
5. ✅ Begin gradual club scraping
6. ✅ Set up automated daily scraping
7. ✅ Monitor and maintain data quality

## Additional Resources

### Scraping Documentation

- **[Scraping Guide](scraping-guide.md)** - Complete ethical scraping guide with robots.txt, rate limiting, workflows
- **[Quick Scraping](quick-scraping.md)** - Quick reference for common scraping tasks

### Other Documentation

- **[Celery Setup](celery-setup.md)** - Optional: Celery configuration (recommended for production)
- **[Deployment Guide](deployment.md)** - Production deployment instructions

## Legal and Ethical Reminders

⚠️ **IMPORTANT**: Always scrape responsibly:

- ✅ Check robots.txt before scraping
- ✅ Review Terms of Service
- ✅ Use proper User-Agent with contact info
- ✅ Respect rate limits (minimum 2 seconds between requests)
- ✅ Only scrape what you need
- ✅ Don't overload servers
- ✅ Handle errors gracefully
- ✅ Monitor your scraping activity
- ✅ Give attribution when displaying data

**Remember**: Web scraping may be subject to legal restrictions. Always ensure you have permission to scrape the target website.

---

---

**Last Updated**: 2026-01-17
**Maintained by**: sunr4y
