# FKAPI – Football Kit Archive API

<p align="center">
  <a href="https://codecov.io/gh/sunr4y/fkapi">
    <img src="https://codecov.io/gh/sunr4y/fkapi/graph/badge.svg?token=GK17MP3KNY" alt="codecov" />
  </a>
  <a href="https://sonarcloud.io/summary/new_code?id=sunr4y_fkapi">
    <img src="https://sonarcloud.io/api/project_badges/measure?project=sunr4y_fkapi&metric=alert_status&token=98224e19ab308456580633cd3ce07e0f37a4b083" alt="Quality Gate Status" />
  </a>
  <a href="https://sonarcloud.io/summary/new_code?id=sunr4y_fkapi">
    <img src="https://sonarcloud.io/api/project_badges/measure?project=sunr4y_fkapi&metric=bugs&token=98224e19ab308456580633cd3ce07e0f37a4b083" alt="Bugs" />
  </a>
  <a href="https://sonarcloud.io/summary/new_code?id=sunr4y_fkapi">
    <img src="https://sonarcloud.io/api/project_badges/measure?project=sunr4y_fkapi&metric=ncloc&token=98224e19ab308456580633cd3ce07e0f37a4b083" alt="Lines of Code" />
  </a>
  <a href="https://sonarcloud.io/summary/new_code?id=sunr4y_fkapi">
    <img src="https://sonarcloud.io/api/project_badges/measure?project=sunr4y_fkapi&metric=security_rating&token=98224e19ab308456580633cd3ce07e0f37a4b083" alt="Security Rating" />
  </a>
  <a href="https://sonarcloud.io/summary/new_code?id=sunr4y_fkapi">
    <img src="https://sonarcloud.io/api/project_badges/measure?project=sunr4y_fkapi&metric=sqale_rating&token=98224e19ab308456580633cd3ce07e0f37a4b083" alt="Maintainability Rating" />
  </a>
  <a href="https://sonarcloud.io/summary/new_code?id=sunr4y_fkapi">
    <img src="https://sonarcloud.io/api/project_badges/measure?project=sunr4y_fkapi&metric=vulnerabilities&token=98224e19ab308456580633cd3ce07e0f37a4b083" alt="Vulnerabilities" />
  </a>

</p>

## Documentation Index

Welcome to the Football Kit Archive API documentation. This index will help you find the information you need.

## About This Project

The Football Kit Archive API is a Django-based REST API that provides access to a comprehensive database of football (soccer) kit information. The project scrapes and aggregates data from public sources to create a searchable, filterable API for kit enthusiasts, developers, and researchers.

**Relation to FootyCollect:** This API is an external service used by [FootyCollect](https://github.com/sunr4y/FootyCollect) to create and manage kits, import images, and handle all related data. FootyCollect can run without it, but the API is practically essential for the full experience.

**Key Features:**
- RESTful API with Django Ninja
- Comprehensive kit database (clubs, seasons, brands, types)
- Advanced search and filtering capabilities
- Ethical web scraping with rate limiting
- Optional Celery integration for background tasks
- Redis caching for improved performance
- Full API documentation with Swagger UI

## Disclaimer

⚠️ **This is a personal learning project** - This project was created for educational purposes and to practice development skills. It is not intended for commercial use or production deployment without proper review and modifications.

**Important Notes:**
- This project is for **learning and skill development** purposes
- Code quality, architecture decisions, and implementations reflect a learning journey
- Some features may be experimental or incomplete
- Always review and test thoroughly before using in any production environment
- The project respects robots.txt and implements ethical scraping practices

## Table of Contents

1. [About This Project](#about-this-project)
2. [Disclaimer](#disclaimer)
3. [Getting Started](#getting-started)
4. [Core Documentation](#core-documentation)
5. [Development](#development)
6. [Operations](#operations)
7. [Quick Reference](#quick-reference)
8. [Finding Information](#finding-information)
9. [Documentation Standards](#documentation-standards)
10. [How to Access Documentation](#how-to-access-documentation)

---

## Getting Started

| Goal | Document |
|------|----------|
| Complete setup from scratch (including initial data population and ethical scraping practices) | **[Getting Started Guide](getting-started.md)** |
| Join the project as a new developer | **[Developer Onboarding](developer-onboarding.md)** |

## Core Documentation

### Setup and Configuration

| Topic | Document |
|-------|----------|
| End‑to‑end setup (with or without Celery) | **[Getting Started](getting-started.md)** |
| Background jobs with Celery (recommended for production) | **[Celery Setup](celery-setup.md)** |
| System architecture and design decisions | **[Architecture](architecture.md)** |
| Data flow through the system | **[Data Flow](data-flow.md)** |
| Production deployment | **[Deployment Guide](deployment.md)** |

### Scraping

| Topic | Document |
|-------|----------|
| Full guide to ethical scraping | **[Scraping Guide](scraping-guide.md)** |
| Quick reference for common scraping tasks | **[Quick Scraping](quick-scraping.md)** |

These guides cover:
- Ethical scraping practices (robots.txt, Terms of Service)
- Rate limiting and delays
- Initial data population workflow
- Daily automated scraping
- Troubleshooting

### API Documentation

| Purpose | Resource |
|---------|----------|
| Interactive Swagger/OpenAPI interface (when server is running) ⭐ | **[Interactive API Docs](http://localhost:8000/api/docs)** |
| Browse all available endpoints | **[API Endpoint Catalog](api/endpoint-catalog.md)** |
| See code examples for using the API | **[API Usage Examples](api/usage-examples.md)** |
| Import endpoints into Postman | **[Postman Collection](api/Football-Kit-Archive-API.postman_collection.json)** |

### Performance and Optimization

| Topic | Document |
|-------|----------|
| Caching implementation and configuration | **[Caching Strategy](caching-strategy.md)** |

## Development

### Architecture Decisions

| Decision | Document |
|----------|----------|
| Scraping framework choice | **[0001: Scraping Framework](decisions/0001-scraping-framework.md)** |
| Tooling and standards | **[0002: Tooling and Standards](decisions/0002-tooling-and-standards.md)** |


## Operations

| Topic | Document |
|-------|----------|
| Common issues and solutions | **[Troubleshooting](troubleshooting.md)** |

## Quick Reference

### Starting Services

**Windows:**
```bash
# Celery Worker
fkapi\start_celery_worker.bat

# Celery Beat
fkapi\start_celery_beat.bat
```

**Linux/Mac:**
```bash
# Celery Worker
./fkapi/start_celery_worker.sh

# Celery Beat
./fkapi/start_celery_beat.sh
```

### Common Commands

```bash
# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Scrape latest kits
python manage.py scrape_latest --start-page 1 --end-page 5

# Scrape a club
python manage.py scrape_whole_club --club-slug "arsenal-kits"

# Run tests
pytest

# Lint code
ruff check .
ruff format .
```

## Finding Information

### I want to...

| I want to… | Go to… |
|-----------|--------|
| Set up the project from scratch (with or without Celery) | **[Getting Started Guide](getting-started.md)** |
| Configure Celery (optional, recommended for production) | **[Celery Setup](celery-setup.md)** |
| Learn about ethical scraping | **[Scraping Guide](scraping-guide.md)** |
| Get a quick scraping reference | **[Quick Scraping](quick-scraping.md)** |
| Deploy to production | **[Deployment Guide](deployment.md)** |
| Understand the architecture | **[Architecture](architecture.md)** |
| Explore all API endpoints | **[API Endpoint Catalog](api/endpoint-catalog.md)** |
| Troubleshoot issues | **[Troubleshooting](troubleshooting.md)** |
| Review architectural decisions | **[Decision Records](decisions/)** |
| Onboard as a developer | **[Developer Onboarding](developer-onboarding.md)** |

## Documentation Standards

All documentation should:
- Be written in English
- Use clear, concise language
- Include code examples where relevant
- Be kept up to date with code changes
- Follow markdown best practices

## How to Access Documentation

### API Documentation (Interactive) ⭐ **PRIMARY**

**Django Ninja automatically generates an interactive API documentation interface.**

1. Start the Django server:
   ```bash
   cd fkapi
   python manage.py runserver
   ```

2. Open your browser:
   ```text
   http://localhost:8000/api/docs
   ```

**Features:**
- Interactive Swagger UI
- Test endpoints directly from browser
- View request/response schemas
- See authentication requirements
- Download OpenAPI schema

### Project Documentation (Markdown)

**Access Methods:**
1. **Direct File Access**: Open `.md` files in your IDE or text editor
2. **GitHub Web Interface**: View formatted documentation when pushed to repository
3. **Local Server**: Use `python -m http.server` or MkDocs (see [Documentation Access Guide](documentation-access.md))

For detailed information, see: **[Documentation Access Guide](documentation-access.md)**

## External Resources

- **Django Documentation**: https://docs.djangoproject.com/
- **Celery Documentation**: https://docs.celeryq.dev/
- **Redis Documentation**: https://redis.io/docs/

---

**Last Updated**: 2026-03-02
**Maintained by**: sunr4y
