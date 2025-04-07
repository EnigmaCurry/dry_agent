#!/bin/sh
set -e

TLS_CERT_FILE="/certs/self.crt"
TLS_KEY_FILE="/certs/self.key"
TLS_CN=${TLS_CN:-localhost}
TLS_EXPIRES=${TLS_EXPIRES:-3650}
TLS_ECC_CURVE=${TLS_ECC_CURVE:-prime256v1}  # Default ECC curve

if [ ! -f "${TLS_CERT_FILE}" ] || [ ! -f "${TLS_KEY_FILE}" ]; then
    echo "Generating self-signed ECC certificate using curve ${TLS_ECC_CURVE}..."
    mkdir -p /certs
    openssl ecparam -genkey -name "${TLS_ECC_CURVE}" -out "${TLS_KEY_FILE}"
    openssl req -new -x509 \
        -key "${TLS_KEY_FILE}" \
        -out "${TLS_CERT_FILE}" \
        -days "${TLS_EXPIRES}" \
        -subj "/CN=${TLS_CN}"
else
    echo "Using existing TLS certificate in /certs"
fi

exec traefik "$@"
