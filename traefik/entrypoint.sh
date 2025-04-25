#!/bin/sh
set -e

PUBLIC_SUBNET=${PUBLIC_SUBNET:-127.0.0.1/32}
PUBLIC_HOST=${PUBLIC_HOST:-localhost}
PUBLIC_PORT=${PUBLIC_PORT:-8123}
PUBLIC_SSH_PORT=${PUBLIC_SSH_PORT:-2225}
APP_LOCALHOST_PORT=${APP_LOCALHOST_PORT:-35123}
SSH_LOCALHOST_PORT=${SSH_LOCALHOST_PORT:-35222}

TLS_CERT_FILE="/certs/self.crt"
TLS_KEY_FILE="/certs/self.key"
TLS_EXPIRES=${TLS_EXPIRES:-3650}
TLS_ECC_CURVE=${TLS_ECC_CURVE:-prime256v1}  # Default ECC curve

CERT_META_FILE="/certs/self.host.txt"

if [ ! -f "${TLS_CERT_FILE}" ] || [ ! -f "${TLS_KEY_FILE}" ] || [ ! -f "$CERT_META_FILE" ] || [ "$(cat "$CERT_META_FILE")" != "$PUBLIC_HOST" ]; then
    echo "Generating self-signed ECC certificate using curve ${TLS_ECC_CURVE}..."
    mkdir -p /certs
    openssl ecparam -genkey -name "${TLS_ECC_CURVE}" -out "${TLS_KEY_FILE}"
    openssl req -new -x509 \
        -key "${TLS_KEY_FILE}" \
        -out "${TLS_CERT_FILE}" \
        -days "${TLS_EXPIRES}" \
        -subj "/CN=${PUBLIC_HOST}"
    echo "$PUBLIC_HOST" > "$CERT_META_FILE"
else
    echo "Using existing TLS certificate in /certs (for CN=${PUBLIC_HOST})"
fi

mkdir -p /etc/traefik
envsubst < /template/traefik.template.yaml > /etc/traefik/traefik.yaml
envsubst < /template/dynamic.template.yaml > /etc/traefik/dynamic.yaml

exec traefik "$@"
