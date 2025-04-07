#!/bin/sh
set -e

TLS_CERT_FILE="/certs/self.crt"
TLS_KEY_FILE="/certs/self.key"
TLS_CN=${TLS_CN:-localhost}
TLS_EXPIRES=${TLS_EXPIRES:-3650}

if [ ! -f "${TLS_CERT_FILE}" ] || [ ! -f "${TLS_KEY_FILE}" ]; then
    echo "Generating self-signed certificate..."
    mkdir -p /certs
    openssl req -x509 -nodes -newkey rsa:2048 \
        -keyout "${TLS_KEY_FILE}" \
        -out "${TLS_CERT_FILE}" \
        -days "${TLS_EXPIRES}" \
        -subj "/CN=${TLS_CN}"
else
    echo "Using existing TLS certificate in /certs"
fi

exec traefik "$@"
