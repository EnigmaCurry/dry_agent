FROM docker.io/library/traefik:v3.3

RUN apk add --no-cache openssl gettext

RUN mkdir /template
COPY traefik.template.yaml dynamic.template.yaml /template

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV TLS_CN=localhost
ENV TLS_EXPIRES=3650

ENTRYPOINT ["/entrypoint.sh"]
