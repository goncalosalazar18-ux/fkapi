# Documentation Index

[![codecov](https://codecov.io/gh/sunr4y/fkapi/graph/badge.svg?token=GK17MP3KNY)](https://codecov.io/gh/sunr4y/fkapi)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=sunr4y_fkapi&metric=alert_status&token=98224e19ab308456580633cd3ce07e0f37a4b083)](https://sonarcloud.io/summary/new_code?id=sunr4y_fkapi)
[![Bugs](https://sonarcloud.io/api/project_badges/measure?project=sunr4y_fkapi&metric=bugs&token=98224e19ab308456580633cd3ce07e0f37a4b083)](https://sonarcloud.io/summary/new_code?id=sunr4y_fkapi)
[![Lines of Code](https://sonarcloud.io/api/project_badges/measure?project=sunr4y_fkapi&metric=ncloc&token=98224e19ab308456580633cd3ce07e0f37a4b083)](https://sonarcloud.io/summary/new_code?id=sunr4y_fkapi)
[![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=sunr4y_fkapi&metric=security_rating&token=98224e19ab308456580633cd3ce07e0f37a4b083)](https://sonarcloud.io/summary/new_code?id=sunr4y_fkapi)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=sunr4y_fkapi&metric=sqale_rating&token=98224e19ab308456580633cd3ce07e0f37a4b083)](https://sonarcloud.io/summary/new_code?id=sunr4y_fkapi)
[![Vulnerabilities](https://sonarcloud.io/api/project_badges/measure?project=sunr4y_fkapi&metric=vulnerabilities&token=98224e19ab308456580633cd3ce07e0f37a4b083)](https://sonarcloud.io/summary/new_code?id=sunr4y_fkapi)
[![Quality gate](https://sonarcloud.io/api/project_badges/quality_gate?project=sunr4y_fkapi&token=98224e19ab308456580633cd3ce07e0f37a4b083)](https://sonarcloud.io/summary/new_code?id=sunr4y_fkapi)

Welcome to the Football Kit Archive API documentation. This index will help you find the information you need.

## About This Project

The Football Kit Archive API is a Django-based REST API that provides access to a comprehensive database of football (soccer) kit information. The project scrapes and aggregates data from public sources to create a searchable, filterable API for kit enthusiasts, developers, and researchers.

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

- **[Getting Started Guide](getting-started.md)** - Complete setup guide from scratch, including initial database population and ethical scraping practices
- **[Developer Onboarding](developer-onboarding.md)** - Guide for new developers joining the project

## Core Documentation

### Setup and Configuration

- **[Getting Started](getting-started.md)** - Complete setup guide from scratch (works with or without Celery)
- **[Celery Setup](celery-setup.md)** - Optional: Guide to setting up Celery for background tasks (recommended for production)
- **[Architecture](architecture.md)** - System architecture and design decisions
- **[Data Flow](data-flow.md)** - How data flows through the system
- **[Deployment Guide](deployment.md)** - Production deployment instructions

### Scraping

- **[Scraping Guide](scraping-guide.md)** - Comprehensive guide to ethical web scraping
- **[Quick Scraping](quick-scraping.md)** - Quick reference for common scraping tasks

These guides cover:
- Ethical scraping practices (robots.txt, Terms of Service)
- Rate limiting and delays
- Initial data population workflow
- Daily automated scraping
- Troubleshooting

### API Documentation

- **[Interactive API Docs](http://localhost:8000/api/docs)** - Swagger/OpenAPI interface (when server is running) ⭐
- **[API Endpoint Catalog](api/endpoint-catalog.md)** - Complete list of API endpoints
- **[API Usage Examples](api/usage-examples.md)** - Code examples for using the API
- **[Postman Collection](api/Football-Kit-Archive-API.postman_collection.json)** - Import this into Postman for testing

### Performance and Optimization

- **[Caching Strategy](caching-strategy.md)** - How caching is implemented and configured

## Development

### Architecture Decisions

- **[Decision Records](decisions/)** - Architecture Decision Records (ADRs)
  - [0001: Scraping Framework](decisions/0001-scraping-framework.md)
  - [0002: Tooling and Standards](decisions/0002-tooling-and-standards.md)


## Operations

- **[Troubleshooting](troubleshooting.md)** - Common issues and solutions

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

- **Set up the project from scratch** → [Getting Started Guide](getting-started.md)
- **Set up without Celery** → [Getting Started Guide](getting-started.md) (works without Celery)
- **Configure Celery (optional)** → [Celery Setup](celery-setup.md) (recommended for production)
- **Learn about ethical scraping** → [Scraping Guide](scraping-guide.md)
- **Quick scraping reference** → [Quick Scraping](quick-scraping.md)
- **Deploy to production** → [Deployment Guide](deployment.md)
- **Understand the architecture** → [Architecture](architecture.md)
- **Use the API** → [API Endpoint Catalog](api/endpoint-catalog.md)
- **Troubleshoot issues** → [Troubleshooting](troubleshooting.md)
- **Understand decisions** → [Decision Records](decisions/)
- **Onboard as developer** → [Developer Onboarding](developer-onboarding.md)

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

**Last Updated**: 2026-01-17
**Maintained by**: sunr4y
