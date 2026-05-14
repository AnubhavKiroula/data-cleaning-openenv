# Multi-stage Dockerfile for production
# Builder stage: install dependencies into a virtualenv
FROM python:3.11-slim as builder

WORKDIR /app

# Install build deps required for some wheels (kept minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./

# Create isolated venv and install packages
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip setuptools wheel \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# Final stage: runtime image
FROM python:3.11-slim

# Install runtime deps (postgres client + curl for healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/opt/venv/bin:$PATH"
WORKDIR /app

# Create non-root user and upload dirs
RUN useradd --create-home --shell /bin/bash app \
    && mkdir -p /app/uploads \
    && chown -R app:app /app /app/uploads

# Copy virtualenv from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY . .

# Ensure entrypoint is executable
RUN chmod +x ./entrypoint.sh

# Switch to non-root user
USER app

EXPOSE 8000

# Lightweight healthcheck hitting FastAPI health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -f http://localhost:8000/api/health || exit 1

ENTRYPOINT ["./entrypoint.sh"]

