FROM python:3.11-slim

# system deps for cryptography, matrix-nio, etc.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential libssl-dev libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# install Poetry
RUN pip install --no-cache-dir poetry

WORKDIR /app

# install dependencies
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
  && poetry install --no-interaction --no-ansi --without dev --no-root

# copy bot code
COPY bot bot

ENV PYTHONUNBUFFERED=1

VOLUME /data

CMD ["python", "-m", "bot"]
