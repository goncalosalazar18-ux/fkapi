# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.2] - 2026-02-04

### Added
- **Bulk kits endpoint**: `GET /api/kits/bulk` accepting comma-separated slugs or full URLs (min 2, max 30 kits), returning a reduced schema; input order preserved
- **User collection API**: `GET /api/user-collection/{userid}` with pagination; `POST /api/user-collection/{userid}/scrape` to trigger scrape (cached 1 week or async via Celery)
- User collection scraper with filtering (skip entries with custom_* fields), pagination, proxy support, and data enrichment (brands, clubs, user info from `/api/user.php`)
- IP whitelist support for rate limiting via `.env`
- Management command `clean_double_slash_urls` to fix double slashes in URL fields (Brand, Club, Competition, Kit)
- HTML sanitization for documentation rendering (safe tag whitelist) to mitigate XSS
- SonarCloud badges in documentation README
- Test cache clearing in setUp/tearDown for better isolation; improved Celery mock handling in tests

### Changed
- Healthcheck now uses `http.client.HTTPConnection` and accepts 200 or 301 (fixes failure when `SECURE_SSL_REDIRECT` redirects to HTTPS)
- `.env.example` and docker-compose updated for `DJANGO_SECRET_KEY`; Celery script errors written to stderr
- Cache invalidation in `cache_utils` refactored around a dictionary of model invalidators
- Scrapers: HTML parser constant, season slug normalization, ReDoS-safe slug parsing; reduced cognitive complexity across multiple functions
- API and docs views refactored to reduce cognitive complexity; docs restricted to GET and sanitized output
- `scrape_user` management command uses the new user collection API scraper
- API documentation (endpoint catalog, usage examples, Postman) updated for bulk and user-collection endpoints

### Removed
- Large `data.json` file from repository
- Legacy views and URL routes: country-assignment, propagation, review, suggest-competition; clubs-without-country, competition-clubs, random-kits/clubs, top-clubs-by-country (API and docs unchanged)

### Fixed
- Healthcheck failing on production due to HTTPS redirect
- Test reliability and cache cross-contamination; `celery_utils` handling of mocks without `__name__`
- Type_K model documentation (translation of "jacket" from Spanish to English)

### Security
- Documentation views restricted to GET; rendered HTML sanitized to prevent XSS
- HTTP method restrictions on assign_countries and suggest_competition_countries views

## [1.0.1] - 2026-01-23

### Added
- Type_K categorization system with automatic categorization for kit types
  - New fields: `category`, `category_order`, `order_priority`, `is_goalkeeper`
  - Management command `categorize_type_k` for bulk categorization
  - Automatic categorization on kit creation during scraping
- Enhanced season search with priority-based ordering
  - Improved search for 4-digit years (e.g., "2025" returns "2025", "2025-26", "2024-25" in correct order)
  - Support for 2-digit year searches (e.g., "97" matches "1997", "1996-97")
  - Uses `first_year` and `second_year` fields for accurate matching
- Secondary team filtering in kit search
  - Prioritizes primary teams over secondary teams (B, C, youth, women's teams)
  - Detects: II, III, B, C, Jong, Youth, U17-U23, Ladies, Women, Femenino, Féminas, Féminine, Lads, Frauen
- Management commands for season cleanup
  - `delete_future_seasons`: Delete seasons with incorrect future years and save kit slugs
  - `rescrape_from_file`: Rescrape kits from a JSON file containing slugs
- Enhanced Django Admin interface for Type_K with new categorization fields

### Changed
- API response now includes Type_K categorization fields (`category`, `category_order`, `order_priority`, `is_goalkeeper`)
- Kit search endpoint now orders results by Type_K category and priority
- Season search endpoint now uses priority-based ordering for better relevance
- Improved error handling and validation across the API

### Fixed
- Fixed season search ordering to prioritize exact matches and relevant results
- Fixed Type_K categorization logic to correctly distinguish "training" from "jacket" types
- Fixed Unicode encoding issues in management commands for Windows compatibility

### Security
- Security improvements from previous releases (headers, validation, etc.)

### Testing
- Added comprehensive tests for Type_K categorization
- Added tests for season search priority ordering
- Added tests for secondary team filtering

## [1.0.0] - 2025-XX-XX

### Initial Release
- Core API functionality
- Kit, Club, Season, Brand, Competition models
- Search and filtering capabilities
- Web scraping integration
- Redis caching
- Celery support (optional)
- API documentation

[1.0.2]: https://github.com/sunr4y/fkapi/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/sunr4y/fkapi/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/sunr4y/fkapi/releases/tag/v1.0.0
