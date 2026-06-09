FROM python:3.10.6-slim AS builder


WORKDIR /app


# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    postgresql-client \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*


# Copy requirements and install Python dependencies
COPY fkapi/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


# Final stage
FROM python:3.10.6-slim


WORKDIR /app


# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*


# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local


# Copy project files
COPY fkapi/ .


# Set Python path
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PATH=/root/.local/bin:$PATH

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 CMD python -c "import http.client; conn = http.client.HTTPConnection('127.0.0.1', int('$PORT' if '$PORT' != '$PORT' else '8000'), timeout=5); conn.request('GET', '/api/health'); resp = conn.getresponse(); exit(0 if resp.status in (200, 301) else 1)" || exit 1

EXPOSE 8000
# Use gunicorn for production
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-8000} --workers 4 --timeout 120 fkapi.wsgi:application"]

