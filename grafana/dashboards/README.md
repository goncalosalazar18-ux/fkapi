# Grafana Dashboards

Custom dashboards for FKApi. The main one is `fkapi-overview.json`.

You can also import these from grafana.com if you want:
- Redis: ID 11835
- PostgreSQL: ID 9628

Custom metrics we track:
- fkapi_user_collection_scrapes_total
- fkapi_user_collection_scrape_duration_seconds
- fkapi_cache_entries
- Plus the standard django-prometheus metrics
