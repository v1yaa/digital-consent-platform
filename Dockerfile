# ============================================================
# Dockerfile – Digital Consent and Data Permission Management Platform
# Base image: python:3.12-slim (Debian slim, minimal attack surface)
# Production WSGI server: Gunicorn
# Runs as non-root user 'appuser'
# ============================================================

FROM python:3.12-slim

# ---------- Build-time metadata ----------
LABEL maintainer="ConsentVault"
LABEL description="Digital Consent and Data Permission Management Platform"
LABEL version="1.0"

# ---------- Environment ----------
# Prevent .pyc files and enable unbuffered stdout/stderr for log visibility
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Default database path – overridden by docker-compose.yml
    DATABASE_URL=sqlite:////data/consent.db \
    PORT=8000

# ---------- Working directory ----------
WORKDIR /app

# ---------- System dependencies ----------
# gcc is needed for some Python C extensions; remove build tools after install
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# ---------- Python dependencies ----------
# Copy requirements first to exploit Docker layer caching:
# this layer is only rebuilt when requirements.txt changes.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ---------- Application source ----------
COPY app/ ./app/
COPY wsgi.py .

# ---------- Persistent data directory ----------
# The SQLite database is stored at /data/consent.db.
# This directory is mounted as a named Docker volume in production.
RUN mkdir -p /data

# ---------- Non-root user ----------
RUN useradd --no-create-home --shell /bin/false appuser && \
    chown -R appuser:appuser /app /data

USER appuser

# ---------- Port ----------
EXPOSE 8000

# ---------- Health check ----------
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# ---------- Entrypoint ----------
# Gunicorn: 2 worker processes, bind to all interfaces on PORT.
CMD ["gunicorn", "--workers", "2", "--bind", "0.0.0.0:8000", "--timeout", "60", "--access-logfile", "-", "wsgi:app"]
