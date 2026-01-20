# Architecture Overview

This document provides a high-level overview of the Football Kit Archive API architecture.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Client Layer                          │
│  (Web Browsers, Mobile Apps, API Clients)                   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      Django Application                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              URL Routing (urls.py)                    │  │
│  └──────────────────┬───────────────────────────────────┘  │
│                     │                                        │
│  ┌──────────────────▼───────────────────────────────────┐  │
│  │              Middleware Layer                          │  │
│  │  • Rate Limiting                                       │  │
│  │  • Performance Monitoring                             │  │
│  └──────────────────┬───────────────────────────────────┘  │
│                     │                                        │
│  ┌──────────────────▼───────────────────────────────────┐  │
│  │              API Layer (Django Ninja)                  │  │
│  │  • REST API Endpoints                                 │  │
│  │  • Request Validation                                │  │
│  │  • Response Serialization                            │  │
│  └──────────────────┬───────────────────────────────────┘  │
│                     │                                        │
│  ┌──────────────────▼───────────────────────────────────┐  │
│  │              Service Layer                             │  │
│  │  • Business Logic                                     │  │
│  │  • Data Processing                                    │  │
│  └──────────────────┬───────────────────────────────────┘  │
│                     │                                        │
│  ┌──────────────────▼───────────────────────────────────┐  │
│  │              Data Access Layer                         │  │
│  │  • Django ORM                                         │  │
│  │  • Model Queries                                      │  │
│  └──────────────────┬───────────────────────────────────┘  │
└─────────────────────┼───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    Data Storage Layer                        │
│  ┌──────────────┐  ┌──────────────┐                       │
│  │  PostgreSQL  │  │    Redis     │                       │
│  │   Database   │  │    Cache     │                       │
│  └──────────────┘  └──────────────┘                       │
│                                                             │
│  Note: Images are stored as URLs pointing to               │
│  footballkitarchive.com, not served locally                │
└─────────────────────────────────────────────────────────────┘
```

## Component Overview

### 1. Client Layer
- Web browsers accessing the frontend
- Mobile applications
- Third-party API clients
- Postman/API testing tools

### 2. Django Application

#### URL Routing
- Maps HTTP requests to appropriate views/endpoints
- Defined in `fkapi/urls.py`
- Supports both API endpoints and admin views

#### Middleware Layer
- **Rate Limiting**: Prevents abuse by limiting requests per IP
- **Performance Monitoring**: Tracks response times and database queries
- Executes before and after request processing

#### API Layer (Django Ninja)
- RESTful API endpoints
- Automatic request/response validation
- OpenAPI/Swagger documentation generation
- Error handling and serialization

#### Service Layer
- Encapsulates business logic
- Separates concerns from views and data access
- Located in `core/services/`
- **KitsService**: Kit-related operations
- **ClubsService**: Club-related operations
- **ScrapingService**: Scraping orchestration

#### Data Access Layer
- Django ORM for database operations
- Model definitions in `core/models.py`
- Query optimization with `select_related` and `prefetch_related`

### 3. Data Storage Layer

#### PostgreSQL Database
- Primary data store
- Stores all models: Club, Kit, Season, Brand, Competition, etc.
- Supports complex queries and relationships

#### Redis Cache
- Caching layer for frequently accessed data
- Reduces database load
- Stores API responses and search results
- Cache invalidation via Django signals

#### External Image URLs
- Images (kit photos, logos) are stored as URLs pointing to footballkitarchive.com
- We do not host or serve static files
- All image URLs reference the source website directly

## Data Flow

### API Request Flow

```
1. Client Request
   ↓
2. URL Routing (urls.py)
   ↓
3. Middleware (Rate Limiting, Performance Monitoring)
   ↓
4. API Endpoint (Django Ninja)
   ↓
5. Service Layer (Business Logic)
   ↓
6. Data Access Layer (Django ORM)
   ↓
7. Database Query
   ↓
8. Response Serialization
   ↓
9. Middleware (Add Headers, Logging)
   ↓
10. Client Response
```

### Scraping Flow

```
1. Management Command Triggered
   ↓
2. ScrapingService.process_kit_data()
   ↓
3. HTTP Request (core/http.py)
   ↓
4. HTML Parsing (core/parsers.py)
   ↓
5. ClubsService.handle_club_changes()
   ↓
6. KitsService.create_or_update_kit()
   ↓
7. Database Save
   ↓
8. Cache Invalidation (Signals)
```

## Key Design Patterns

### 1. Service Layer Pattern
- Separates business logic from views
- Makes code more testable and maintainable
- Located in `core/services/`

### 2. Repository Pattern (via Django ORM)
- Data access abstraction
- Model managers for complex queries

### 3. Middleware Pattern
- Cross-cutting concerns (rate limiting, monitoring)
- Executes on every request

### 4. Signal Pattern
- Cache invalidation
- Automatic cleanup on model changes

### 5. Factory Pattern
- HTTP session creation
- Scraper configuration

## Technology Stack

- **Framework**: Django 5.0
- **API**: Django Ninja
- **Database**: PostgreSQL
- **Cache**: Redis
- **Task Queue**: Celery (optional)
- **HTTP Client**: requests
- **HTML Parsing**: BeautifulSoup4
- **Testing**: pytest, pytest-django
- **Linting**: Ruff

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Load Balancer                           │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┴───────────────┐
         │                               │
         ▼                               ▼
┌─────────────────┐           ┌─────────────────┐
│  Django App 1   │           │  Django App 2   │
│  (Gunicorn)     │           │  (Gunicorn)     │
└────────┬────────┘           └────────┬────────┘
         │                               │
         └───────────────┬───────────────┘
                         │
         ┌───────────────┴───────────────┐
         │                               │
         ▼                               ▼
┌─────────────────┐           ┌─────────────────┐
│   PostgreSQL    │           │     Redis      │
│   (Primary)     │           │     Cache      │
└─────────────────┘           └─────────────────┘
```

## Security Considerations

- Rate limiting to prevent abuse
- Optional API key authentication
- CSRF protection (disabled for API endpoints)
- SQL injection protection (via Django ORM)
- XSS protection (via Django templates)
- Secure headers via middleware

## Performance Optimizations

- Redis caching for frequently accessed data
- Database query optimization (select_related, prefetch_related)
- Database indexes on frequently queried fields
- Response compression (via middleware)
- Connection pooling (database and Redis)
