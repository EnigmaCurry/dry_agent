#!/usr/bin/env bash
set -euo pipefail

# Where Podman mounts your cert volumes:
CERT_DIR_CA="/certs/CA"
CERT_DIR_TRAEFIK="/certs/traefik"
CERT_DIR_APP="/certs/app"
CERT_DIR_AUTH="/certs/auth"

# Make sure the host-mounted dirs exist
mkdir -p "$CERT_DIR_CA" "$CERT_DIR_TRAEFIK" "$CERT_DIR_APP" "$CERT_DIR_AUTH"

# 100-year expiry (100 yr × 365 d/yr × 24 h/d = 876000h)
NOT_AFTER="876000h"

# 1) Root CA
if [[ ! -f "$CERT_DIR_CA/dry-agent-root.crt" || ! -f "$CERT_DIR_CA/dry-agent-root.key" ]]; then
  echo "Generating Root CA..."
  step certificate create "dry-agent Root CA" \
    "$CERT_DIR_CA/dry-agent-root.crt" "$CERT_DIR_CA/dry-agent-root.key" \
    --profile root-ca \
    --not-after "$NOT_AFTER" \
    --no-password \
    --insecure
else
  echo "Root CA already exists, skipping"
fi

# Helper function to issue a service cert once
issue_cert() {
  local NAME=$1
  local DIR=$2
  local CRT="$DIR/${NAME// /_}.crt"
  local KEY="$DIR/${NAME// /_}.key"

  if [[ ! -f "$CRT" || ! -f "$KEY" ]]; then
    echo "Issuing cert for '$NAME'..."
    step certificate create "$NAME" \
      "$CRT" "$KEY" \
      --ca "$CERT_DIR_CA/dry-agent-root.crt" \
      --ca-key "$CERT_DIR_CA/dry-agent-root.key" \
      --not-after "$NOT_AFTER" \
      --san 127.0.0.1 \
      --san localhost \
      --no-password \
      --insecure
  else
    echo "Cert for '$NAME' already exists, skipping"
  fi
}

# 2) Traefik
issue_cert "dry-agent Traefik" "$CERT_DIR_TRAEFIK"

# 3) App
issue_cert "dry-agent App" "$CERT_DIR_APP"

# 4) Auth
issue_cert "dry-agent Auth" "$CERT_DIR_AUTH"

# 5) Copy the Root CA cert to each service cert volume
for d in "$CERT_DIR_TRAEFIK" "$CERT_DIR_APP" "$CERT_DIR_AUTH"; do
  if [[ -f "$CERT_DIR_CA/dry-agent-root.crt" ]]; then
    echo "Copying Root CA to $d/"
    cp -f "$CERT_DIR_CA/dry-agent-root.crt" "$d/dry-agent-root.crt"
  fi
done
