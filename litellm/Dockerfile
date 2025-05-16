ARG LITELLM_VERSION=main-latest
FROM ghcr.io/berriai/litellm:${LITELLM_VERSION}

COPY config.yaml /app/config.yaml

CMD ["--host", "127.0.0.1", "--port", "4000", "--config", "/app/config.yaml", "--debug"]
