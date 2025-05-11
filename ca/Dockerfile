FROM docker.io/smallstep/step-cli:latest

USER root
# Copy in our init script
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Override PUBLIC_HOST to set the TLS CN for Traefik.
ENV PUBLIC_HOST=127.0.0.1
# Override TLS_EXPIRES to set the default TLS cert expiration (in hours).
ENV TLS_EXPIRES=876000h
# Override CA_EXPIRES to set the default CA cert expiration (in hours).
ENV CA_EXPIRES=876000h

User step

ENTRYPOINT ["entrypoint.sh"]
