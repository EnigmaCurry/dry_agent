FROM docker.io/library/traefik:v3.3

RUN apk add --no-cache openssl

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV TLS_CN=localhost
ENV TLS_EXPIRES=3650

ENTRYPOINT ["/entrypoint.sh"]
