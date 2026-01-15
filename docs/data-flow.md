# Data Flow Diagrams

This document describes the data flow through the Football Kit Archive API system.

## API Request Flow

### Standard API Request

```
┌─────────┐
│ Client  │
└────┬────┘
     │ HTTP Request
     ▼
┌─────────────────┐
│  URL Router     │  (urls.py)
│  /api/...       │
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│ Rate Limiting   │  (middleware.py)
│ Middleware      │  • Check IP rate limit
└────┬────────────┘  • Increment counter
     │
     ▼
┌─────────────────┐
│ Performance     │  (middleware.py)
│ Monitoring      │  • Start timer
│ Middleware      │  • Count queries
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│ API Endpoint    │  (api.py)
│ (Django Ninja)  │  • Validate request
└────┬────────────┘  • Parse parameters
     │
     ▼
┌─────────────────┐
│ Cache Check     │  (cache_utils.py)
│                 │  • Generate cache key
└────┬────────────┘  • Check Redis
     │
     ├─── Cache Hit ───┐
     │                 │
     ▼                 ▼
┌─────────┐      ┌──────────────┐
│ Return  │      │ Service      │
│ Cached  │      │ Layer        │
│ Data    │      │              │
└─────────┘      └──────┬───────┘
                        │
                        ▼
                 ┌──────────────┐
                 │ Database      │
                 │ Query        │
                 │ (Django ORM) │
                 └──────┬───────┘
                        │
                        ▼
                 ┌──────────────┐
                 │ Cache Store  │
                 │ (Redis)      │
                 └──────┬───────┘
                        │
                        ▼
                 ┌──────────────┐
                 │ Serialize    │
                 │ Response     │
                 └──────┬───────┘
                        │
                        ▼
                 ┌──────────────┐
                 │ Add Headers   │
                 │ (X-API-Version│
                 │  X-Response-  │
                 │  Time, etc.)  │
                 └──────┬───────┘
                        │
                        ▼
                 ┌──────────────┐
                 │ HTTP Response│
                 │ to Client    │
                 └──────────────┘
```

## Scraping Data Flow

### Kit Scraping Process

```
┌─────────────────────┐
│ Management Command  │
│ scrape_brand.py     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ ScrapingService     │
│ .process_kit_data() │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ HTTP Request         │
│ (core/http.py)       │
│ • Get session        │
│ • Apply proxy        │
│ • Set headers        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ External Website     │
│ (footballkitarchive)│
└──────────┬──────────┘
           │
           │ HTML Response
           ▼
┌─────────────────────┐
│ HTML Parsing         │
│ (core/parsers.py)    │
│ • Extract fact table │
│ • Parse colors       │
│ • Parse season       │
│ • Extract competitions│
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ ClubsService        │
│ .handle_club_       │
│  changes()          │
│ • Check if exists   │
│ • Create/update     │
│ • Handle name changes│
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ KitsService         │
│ .create_or_         │
│  update_kit()       │
│ • Process competitions│
│ • Process colors    │
│ • Create/update kit │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Database Save        │
│ (Django ORM)         │
│ • Save Club          │
│ • Save Kit           │
│ • Save relationships │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Django Signals       │
│ • post_save          │
│ • post_delete        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Cache Invalidation   │
│ (cache_utils.py)     │
│ • Invalidate club    │
│   related cache      │
│ • Invalidate kit     │
│   related cache      │
└─────────────────────┘
```

## Cache Invalidation Flow

### Model Change Triggers Cache Invalidation

```
┌─────────────────────┐
│ Model Change        │
│ (Kit.save(), etc.)  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Django Signal        │
│ (post_save,          │
│  post_delete)        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Cache Utils          │
│ (cache_utils.py)     │
│ • invalidate_kit_   │
│   cache()            │
│ • invalidate_club_   │
│   cache()            │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Redis Cache          │
│ • Delete cache keys  │
│ • Pattern matching   │
└─────────────────────┘
```

## Search Flow

### Club Search with Caching

```
┌─────────────────────┐
│ GET /api/clubs/     │
│ search?keyword=...  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Generate Cache Key  │
│ search_clubs_{keyword}│
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Check Redis Cache   │
└──────────┬──────────┘
           │
     ┌─────┴─────┐
     │           │
  Hit│           │Miss
     │           │
     ▼           ▼
┌─────────┐ ┌─────────────────┐
│ Return   │ │ Database Query  │
│ Cached   │ │ • Trigram search│
│ Result   │ │ • Limit 10      │
└──────────┘ └────────┬────────┘
                      │
                      ▼
               ┌──────────────┐
               │ Store in     │
               │ Cache        │
               │ (30 min TTL) │
               └──────┬───────┘
                      │
                      ▼
               ┌──────────────┐
               │ Return       │
               │ Results      │
               └──────────────┘
```

## Error Handling Flow

### API Error Response

```
┌─────────────────────┐
│ Exception Raised    │
│ (in endpoint/service)│
└──────────┬──────────┘
           │
     ┌─────┴─────┐
     │           │
     ▼           ▼
┌─────────┐ ┌──────────────┐
│ Custom   │ │ Standard     │
│ Exception│ │ Exception    │
│ (core/   │ │ (Python)     │
│  exceptions.py)│          │
└────┬─────┘ └──────┬───────┘
     │              │
     └──────┬───────┘
            │
            ▼
┌─────────────────────┐
│ Exception Handler    │
│ (api.py)             │
│ • Map to HTTP status │
│ • Format response    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Error Response      │
│ {                   │
│   "detail": "..."   │
│ }                   │
└─────────────────────┘
```

## Performance Monitoring Flow

### Request Performance Tracking

```
┌─────────────────────┐
│ Request Received    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Start Timer         │
│ Count Initial       │
│ Queries             │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Process Request     │
│ (endpoint logic)    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Calculate Duration  │
│ Count Final Queries │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Log Performance    │
│ • Response time     │
│ • Query count       │
│ • Slow queries      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Add Response        │
│ Headers             │
│ • X-Response-Time   │
│ • X-Query-Count     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Track API Usage     │
│ (for /metrics)      │
└─────────────────────┘
```
