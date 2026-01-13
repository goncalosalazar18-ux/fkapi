# ADR 0001: Scraping Framework Decision

Status: Accepted
Date: 2025-10-20

## Context

The project scrapes a single external site (footballkitarchive.com) and maps results directly into Django models. The main scraper module is large and mixes concerns (HTTP, parsing, persistence). A reviewer asked whether we should move to a dedicated scraping framework instead of refactoring the current approach.

## Options Considered

1) Keep requests + BeautifulSoup and refactor
- Pros: Minimal migration, smaller cognitive load, easy to unit test with HTML fixtures, integrates simply with Django ORM
- Cons: Lacks built-in concurrency, throttling, caching, and spider lifecycle; needs homegrown utilities

2) Adopt Scrapy
- Pros: Mature framework with spiders, pipelines, middlewares, throttling, caching, robust scheduling and observability
- Cons: Significant rewrite; different execution model; integrating tightly with Django ORM requires careful design; overkill for a single source and modest concurrency

3) Headless browser tools (Playwright/Selenium)
- Pros: Handles dynamic sites, JS rendering
- Cons: Heavier, slower, increased ops complexity; unnecessary for our static HTML target

4) Hybrid: httpx + parsel/selectolax
- Pros: Faster HTTP client and fast HTML parsing with CSS/XPath; modern APIs
- Cons: Some migration effort; limited added value unless performance is a bottleneck

## Decision

Do not migrate to a dedicated scraping framework at this time. Proceed with incremental refactoring while retaining requests + BeautifulSoup.

Rationale:
- Single source with predictable structure
- Lower operational complexity and fewer moving parts
- Ability to incrementally improve reliability (retries, timeouts, proxy, backoff) without a rewrite

## Consequences

- Implement and use a centralized HTTP client with retries/backoff, default headers, proxies, and timeouts.
- Extract pure parsing functions and unit test them with fixtures.
- Maintain a clear seam between parsing (pure) and persistence (transactional).
- If scraping scope or concurrency increases significantly, revisit Scrapy as an option.

## Follow-up Actions

- [x] Add core/http.py with standardized session, headers, retries, and helper function.
- [x] Extract parsing helpers from core/scrapers.py and cover them with unit tests.
- [x] Replace print debugging with logging.
- [ ] Optionally evaluate httpx + selectolax if performance becomes a concern.
