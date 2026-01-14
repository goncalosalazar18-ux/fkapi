# Troubleshooting FAQ

Common issues and solutions for the Football Kit Archive API.

## Setup Issues

### Database Connection Errors

**Problem**: `django.db.utils.OperationalError: could not connect to server`

**Solutions**:
1. Verify PostgreSQL is running:
   ```bash
   # On Linux/Mac
   sudo systemctl status postgresql
   
   # On Windows
   # Check Services panel
   ```

2. Check database credentials in `.env`:
   ```
   DATABASE_URL=postgresql://user:password@localhost:5432/fkapi
   ```

3. Create database if it doesn't exist:
   ```bash
   createdb fkapi
   ```

4. Test connection:
   ```bash
   psql -U user -d fkapi -h localhost
   ```

### Redis Connection Errors

**Problem**: `ConnectionError: Error connecting to Redis`

**Solutions**:
1. Verify Redis is running:
   ```bash
   # On Linux/Mac
   redis-cli ping
   # Should return: PONG
   
   # On Windows
   # Check Services panel or use WSL
   ```

2. Check Redis URL in `.env`:
   ```
   REDIS_URL=redis://localhost:6379/1
   ```

3. Start Redis if not running:
   ```bash
   # On Linux/Mac
   redis-server
   
   # On Windows (using WSL or Docker)
   docker run -d -p 6379:6379 redis
   ```

### Module Import Errors

**Problem**: `ModuleNotFoundError: No module named 'core'`

**Solutions**:
1. Ensure you're in the correct directory:
   ```bash
   cd fkapi
   ```

2. Activate virtual environment:
   ```bash
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate      # Windows
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

## Runtime Issues

### Rate Limit Exceeded

**Problem**: `403 Forbidden` with rate limit message

**Solutions**:
1. Wait for rate limit to reset (default: 1 hour)
2. Increase rate limit in `.env`:
   ```
   API_RATE_LIMIT_RATE=200/hour
   ```
3. Use different IP address (if testing)
4. Disable rate limiting in development (not recommended for production)

### Slow API Responses

**Problem**: API responses are slow

**Solutions**:
1. Check Redis cache is working:
   ```bash
   redis-cli ping
   ```

2. Check database query performance:
   - Enable query logging in `settings.py`
   - Review slow query logs
   - Add database indexes if needed

3. Check response time headers:
   ```
   X-Response-Time: 0.123s
   X-Query-Count: 5
   ```

4. Warm cache:
   ```bash
   python manage.py warm_cache
   ```

### Cache Not Working

**Problem**: Cache doesn't seem to be working

**Solutions**:
1. Verify Redis connection (see above)
2. Check cache configuration in `settings.py`
3. Clear cache manually:
   ```bash
   redis-cli FLUSHDB
   ```
4. Check cache keys:
   ```bash
   redis-cli KEYS "fkapi:*"
   ```

### Database Migration Errors

**Problem**: `django.db.migrations.exceptions.InconsistentMigrationHistory`

**Solutions**:
1. Check migration history:
   ```bash
   python manage.py showmigrations
   ```

2. Fake migration if needed (use with caution):
   ```bash
   python manage.py migrate --fake core 0001
   ```

3. Reset migrations (development only):
   ```bash
   # Delete migration files (except __init__.py)
   # Recreate migrations
   python manage.py makemigrations
   python manage.py migrate
   ```

## Testing Issues

### Tests Failing

**Problem**: Tests fail with `ModuleNotFoundError` or import errors

**Solutions**:
1. Ensure test settings are correct in `pytest.ini`:
   ```ini
   DJANGO_SETTINGS_MODULE = test_settings
   pythonpath = fkapi
   ```

2. Run tests from project root:
   ```bash
   pytest fkapi/core/tests/
   ```

3. Check `test_settings.py` has all required configurations

### Coverage Not Working

**Problem**: Coverage report shows 0% or missing files

**Solutions**:
1. Install coverage tools:
   ```bash
   pip install pytest-cov coverage
   ```

2. Run with coverage:
   ```bash
   pytest --cov=fkapi/core --cov-report=html
   ```

3. Check `.coveragerc` or `pyproject.toml` configuration

## Scraping Issues

### Scraping Fails with Connection Errors

**Problem**: `requests.exceptions.ConnectionError` or timeout

**Solutions**:
1. Check internet connection
2. Verify target website is accessible
3. Check proxy settings in `core/http.py`
4. Increase timeout:
   ```python
   timeout=30  # in http_get()
   ```

### HTML Parsing Errors

**Problem**: `AttributeError` or `KeyError` during parsing

**Solutions**:
1. Check if website structure changed
2. Review HTML fixtures in tests
3. Add defensive checks in parsers
4. Log raw HTML for debugging:
   ```python
   logger.debug(f"HTML content: {html[:1000]}")
   ```

### Duplicate Data Issues

**Problem**: Duplicate clubs or kits created

**Solutions**:
1. Check slug uniqueness constraints
2. Use `get_or_create()` instead of `create()`
3. Review merge suggestions:
   ```bash
   python manage.py merge_clubs_from_logs
   ```

## API Issues

### 500 Internal Server Error

**Problem**: API returns 500 error

**Solutions**:
1. Check Django logs: `fkapi/api.log`
2. Enable DEBUG mode temporarily:
   ```
   DJANGO_DEBUG=True
   ```
3. Check database connection
4. Verify all required environment variables are set

### API Documentation Not Loading

**Problem**: `/api/docs` returns 404 or error

**Solutions**:
1. Verify Django Ninja is installed:
   ```bash
   pip install django-ninja
   ```

2. Check URL configuration in `fkapi/urls.py`:
   ```python
   path('api/', api.urls),
   ```

3. Access docs at: `http://localhost:8000/api/docs`

### CORS Errors (if applicable)

**Problem**: CORS errors in browser console

**Solutions**:
1. Install django-cors-headers:
   ```bash
   pip install django-cors-headers
   ```

2. Add to `INSTALLED_APPS`:
   ```python
   'corsheaders',
   ```

3. Add middleware:
   ```python
   'corsheaders.middleware.CorsMiddleware',
   ```

4. Configure allowed origins in `settings.py`

## Performance Issues

### High Database Query Count

**Problem**: Too many database queries per request

**Solutions**:
1. Use `select_related()` for foreign keys:
   ```python
   Kit.objects.select_related('team', 'season')
   ```

2. Use `prefetch_related()` for many-to-many:
   ```python
   Club.objects.prefetch_related('competitions')
   ```

3. Check query count in response headers:
   ```
   X-Query-Count: 15
   ```

### Memory Issues

**Problem**: High memory usage

**Solutions**:
1. Use pagination for large datasets
2. Process data in chunks:
   ```python
   Kit.objects.all().iterator(chunk_size=1000)
   ```
3. Clear cache periodically
4. Monitor with `django-debug-toolbar` (development)

## Getting More Help

1. **Check Logs**: Review `fkapi/api.log` and `fkapi/logs/performance.log`
2. **Enable Debug**: Set `DJANGO_DEBUG=True` for detailed error messages
3. **Check Documentation**: Review `docs/` directory
4. **GitHub Issues**: Search existing issues or create new one
5. **Django Debug Toolbar**: Install for development debugging

## Common Error Messages

### `django.core.exceptions.ImproperlyConfigured`

Usually means missing or incorrect settings. Check:
- Environment variables in `.env`
- Database configuration
- Redis configuration

### `django.db.utils.IntegrityError`

Database constraint violation. Check:
- Unique constraints
- Foreign key relationships
- Required fields

### `ninja.errors.ValidationError`

API request validation failed. Check:
- Required parameters
- Parameter types
- Request body format

### `core.exceptions.ScrapingError`

Scraping operation failed. Check:
- Network connectivity
- Target website availability
- HTML structure changes
