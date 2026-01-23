# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[1.0.1]: https://github.com/sunr4y/fkapi/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/sunr4y/fkapi/releases/tag/v1.0.0
