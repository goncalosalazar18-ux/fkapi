# Grafana Setup

Quick guide for setting up monitoring with Prometheus and Grafana.

## Django Setup

Install: `pip install django-prometheus prometheus-client`

Add to INSTALLED_APPS: `'django_prometheus'`

Add middleware (before and after your existing middleware):
- `django_prometheus.middleware.PrometheusBeforeMiddleware`
- `django_prometheus.middleware.PrometheusAfterMiddleware`

Add to urls.py: `path('', include('django_prometheus.urls'))`

## Docker Compose

Monitoring services use the `monitoring` profile. See `docs/docker-compose-profiles.md` for details.

```bash
# Start with monitoring
docker-compose --profile monitoring up -d
```

## Prometheus Config

Config is in `prometheus/prometheus.yml`. It scrapes:
- Django metrics from `web:8000/metrics`
- Celery metrics from `flower:5555/metrics`
- Redis from `redis_exporter:9121`
- PostgreSQL from `host.docker.internal:9187` (for systemd PostgreSQL)

If you're using Docker PostgreSQL, change the postgres target to `postgres_exporter:9187`.

## Grafana

If using external Grafana (systemd), add Prometheus as data source:
- URL: `http://localhost:9090` (or your Prometheus server IP)
- Type: Prometheus

Import the dashboard from `grafana/dashboards/fkapi-overview.json`.

## Custom Metrics

See `core/metrics.py` for custom metrics definitions. Examples of how to use them are in `docs/metrics-integration-example.md` (not all implemented yet).

## Notes

- Metrics endpoint is at `/metrics` if django-prometheus is installed
- The dashboard JSON was exported from Grafana UI, you can edit it there and re-export
- For PostgreSQL exporter on systemd, see `docs/postgres-exporter-setup.md`
