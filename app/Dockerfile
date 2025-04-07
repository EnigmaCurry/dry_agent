# --------------------
# Build svelte frontend stage
# --------------------
FROM node:23 as frontend-builder
WORKDIR /app/frontend
# Copy only package files first to leverage Docker cache.
COPY frontend/package*.json ./
RUN npm install
# Copy the rest of the Svelte source code.
COPY frontend/ .
# Build the Svelte app (this will output files into the public/build folder).
RUN npm run build

# --------------------
# Build fastapi with poetry
# --------------------
FROM debian:bookworm-slim AS builder

WORKDIR /build

ENV DEBIAN_FRONTEND=noninteractive
ENV PIP_BREAK_SYSTEM_PACKAGES=1

# Install Python 3.11+ and dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl build-essential gcc python3 python3-dev python3-pip python3-venv \
    && pip3 install --upgrade pip \
    && pip3 install poetry \
    && rm -rf /var/lib/apt/lists/*

# Only copy dependency files
COPY pyproject.toml poetry.lock ./

# Prevent poetry from using a venv
RUN poetry config virtualenvs.create false

# Dummy README to satisfy tools
RUN touch README.md

# Install dependencies (without dev or local package)
RUN poetry install --without dev --no-root

# --------------------
# Runtime stage
# --------------------
FROM localhost/dry-agent/workstation

ARG PYTHON_VERSION=3.11

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=80

WORKDIR /app

# Install runtime Python and pip
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Use python3/pip3 as default
RUN ln -s /usr/bin/python3 /usr/local/bin/python && \
    ln -s /usr/bin/pip3 /usr/local/bin/pip

# Copy installed site-packages from builder
COPY --from=builder /usr/local/lib/python${PYTHON_VERSION}/dist-packages /usr/local/lib/python${PYTHON_VERSION}/dist-packages

# Copy app code and frontend
COPY app app
COPY --from=frontend-builder /app/frontend/build ./public

# Make entrypoint executable
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8001

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
