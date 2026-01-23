# Developer Onboarding Guide

Guide for new developers joining the project. This document covers setup, project structure, development workflow, and common tasks.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Project Structure](#project-structure)
4. [Development Workflow](#development-workflow)
5. [Key Concepts](#key-concepts)
6. [Common Tasks](#common-tasks)
7. [Debugging](#debugging)
8. [Getting Help](#getting-help)
9. [Next Steps](#next-steps)

---

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.10+**: [Download Python](https://www.python.org/downloads/)
- **PostgreSQL 12+**: [Download PostgreSQL](https://www.postgresql.org/download/)
- **Redis**: [Download Redis](https://redis.io/download)
- **Git**: [Download Git](https://git-scm.com/downloads)

## Initial Setup

### 1. Clone the Repository

```bash
git clone https://github.com/sunr4y/fkapi.git
cd fkapi
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On Linux/Mac
source venv/bin/activate
```

### 3. Install Dependencies

```bash
# Install production dependencies
pip install -r fkapi/requirements.txt

# Install development dependencies
pip install -r fkapi/requirements-dev.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Django Settings
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/fkapi

# Redis
REDIS_URL=redis://localhost:6379/1

# Optional: API Authentication
DJANGO_API_ENABLE_AUTH=False
API_RATE_LIMIT_RATE=100/hour
```

### 5. Set Up Database

```bash
# Create database
createdb fkapi

# Run migrations
cd fkapi
python manage.py migrate
```

### 6. Create Superuser (Optional)

```bash
python manage.py createsuperuser
```

### 7. Run Development Server

```bash
python manage.py runserver
```

The API will be available at `http://localhost:8000/api/`

## Project Structure

```
fkapi/
├── core/                    # Main application code
│   ├── models.py           # Database models
│   ├── views.py            # Django views
│   ├── api.py              # API endpoints (Django Ninja)
│   ├── scrapers.py         # Web scraping logic
│   ├── parsers.py          # HTML parsing
│   ├── services/           # Business logic layer
│   │   ├── kits_service.py
│   │   ├── clubs_service.py
│   │   └── scraping_service.py
│   ├── middleware.py       # Custom middleware
│   ├── cache_utils.py      # Cache utilities
│   └── tests/              # Test files
├── fkapi/                  # Django project settings
│   ├── settings.py         # Main settings
│   ├── urls.py             # URL routing
│   └── api.py              # API configuration
├── docs/                   # Documentation
├── requirements.txt        # Production dependencies
└── requirements-dev.txt   # Development dependencies
```

## Development Workflow

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest fkapi/core/tests/test_api.py

# Run with coverage
pytest --cov=fkapi/core --cov-report=html
```

### Code Quality

```bash
# Check code style
ruff check .

# Auto-fix issues
ruff check --fix .

# Format code
ruff format .
```

### Django Management Commands

```bash
# Run migrations
python manage.py migrate

# Create migrations
python manage.py makemigrations

# Note: We do not serve static files
# Images are stored as URLs pointing to footballkitarchive.com

# Run scraping command
python manage.py scrape_brand adidas

# Warm cache
python manage.py warm_cache
```

## Key Concepts

### Service Layer

Business logic is separated into service classes:
- `KitsService`: Handles kit-related operations
- `ClubsService`: Handles club-related operations
- `ScrapingService`: Orchestrates scraping operations

### Caching Strategy

- Redis is used for caching API responses
- Cache keys follow patterns: `{type}_{id}`, `search_{type}_{keyword}`
- Cache invalidation happens automatically via Django signals

### API Endpoints

All API endpoints are defined in `fkapi/fkapi/api.py` using Django Ninja.
See `docs/api/endpoint-catalog.md` for complete API documentation.

### Testing

- Tests are located in `fkapi/core/tests/`
- Use pytest fixtures for test data
- Test coverage is tracked with pytest-cov

## Common Tasks

### Adding a New API Endpoint

1. Add endpoint function in `fkapi/fkapi/api.py`:

```python
@api.get("/my-endpoint")
def my_endpoint(request: HttpRequest):
    return {"message": "Hello"}
```

2. Add tests in `fkapi/core/tests/test_api.py`
3. Update `docs/api/endpoint-catalog.md`

### Adding a New Model

1. Define model in `fkapi/core/models.py`
2. Create migration: `python manage.py makemigrations`
3. Run migration: `python manage.py migrate`
4. Add to admin in `fkapi/core/admin.py` (if needed)
5. Add tests in `fkapi/core/tests/test_models.py`

### Adding Cache Invalidation

1. Add signal handler in `fkapi/core/cache_utils.py`
2. Connect signal in `fkapi/core/apps.py`
3. Test cache invalidation

## Debugging

### Enable Debug Mode

Set `DJANGO_DEBUG=True` in `.env` file.

### View Logs

Logs are written to:
- `fkapi/api.log`: General application logs
- `fkapi/logs/performance.log`: Performance monitoring logs

### Database Queries

Enable query logging in `settings.py`:
```python
LOGGING = {
    'loggers': {
        'django.db.backends': {
            'level': 'DEBUG',
        },
    },
}
```

## Getting Help

- **Documentation**: Check `docs/` directory
- **API Docs**: Visit `http://localhost:8000/api/docs` when server is running
- **Issues**: Check GitHub issues
- **Code Review**: Follow existing code patterns

## Next Steps

1. Read `docs/architecture.md` for system overview
2. Review `docs/api/endpoint-catalog.md` for API reference
3. Explore existing code in `fkapi/core/`
4. Run tests to understand test patterns
5. Make your first contribution!

## Tips

- Always run tests before committing
- Use type hints for better code clarity
- Follow existing code style (Ruff will help)
- Write docstrings for new functions/classes
- Update documentation when adding features

---

**Last Updated**: 2026-01-17
**Maintained by**: sunr4y
