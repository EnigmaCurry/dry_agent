# --------------------
# Builder stage
# --------------------
FROM python:3.13-slim AS builder

WORKDIR /build

# Install system deps & poetry
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl build-essential gcc \
    && pip install poetry \
    && rm -rf /var/lib/apt/lists/*

# Only copy dependency files first
COPY pyproject.toml poetry.lock ./

# Prevent poetry from using a venv
RUN poetry config virtualenvs.create false

# Ensure README exists (some tools require it)
RUN touch README.md

# Install dependencies only (no dev deps, no local package)
RUN poetry install --without dev --no-root

# --------------------
# Runtime stage
# --------------------
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=80

WORKDIR /app

# Copy installed dependencies from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages

# Copy app code and entrypoint
COPY . .

# Make entrypoint executable
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 80

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
