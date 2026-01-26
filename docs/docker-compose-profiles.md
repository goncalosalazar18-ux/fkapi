# Docker Compose Profiles

Using profiles to make everything optional. Minimal setup is just the web app.

## Minimal Setup (Default)

```bash
docker-compose up -d
```

Starts: web only (uses external PostgreSQL, no Redis/Celery needed)

## With Services

```bash
docker-compose --profile services up -d
```

Adds: db (Docker PostgreSQL), redis, celery, celerybeat, flower

## With Monitoring

```bash
docker-compose --profile monitoring up -d
```

Adds: prometheus, redis_exporter, postgres_exporter, grafana

## Service Profiles

- Always active: web
- Services profile: db, redis, celery, celerybeat, flower
- Monitoring profile: prometheus, redis_exporter, postgres_exporter, grafana

## Notes

- Web works without Redis (uses locmem cache) and without Celery (uses threading fallback)
- Set POSTGRES_HOST to your external PostgreSQL server IP
- Set USE_REDIS_CACHE=False and ENABLE_CELERY=False for minimal setup
