#!/usr/bin/env bash
set -euo pipefail

PUBLIC_HOST=${PUBLIC_HOST:-localhost}

# Base path for all certs
CERT_BASE_DIR="/certs"
CERT_DIR_CA="$CERT_BASE_DIR/CA"

# List of services to generate certs for
SERVICES=(app auth bot)

CA_EXPIRES=${CA_EXPIRES:-876000h}

# 100-year expiry (100 yr × 365 d/yr × 24 h/d = 876000h)
TLS_EXPIRES=${TLS_EXPIRES:-876000h}

# 1) Create CA directory and each service directory
mkdir -p "$CERT_DIR_CA"
for srv in "${SERVICES[@]}"; do
  mkdir -p "$CERT_BASE_DIR/$srv"
done

# 2) Root CA
if [[ ! -f "$CERT_DIR_CA/dry-agent-root.crt" || ! -f "$CERT_DIR_CA/dry-agent-root.key" ]]; then
  echo "Generating Root CA (expires ${CA_EXPIRES}) ..."
  step certificate create "dry-agent Root CA" \
    "$CERT_DIR_CA/dry-agent-root.crt" \
    "$CERT_DIR_CA/dry-agent-root.key" \
    --profile root-ca \
    --not-after "$CA_EXPIRES" \
    --no-password \
    --insecure
else
  echo "Root CA already exists, skipping"
fi

# 3) Helper to issue a cert for a given service
issue_cert() {
  local service="$1"
  local cap="${service^}"  # Capitalize first letter
  local dir="$CERT_BASE_DIR/$service"
  local crt="$dir/dry-agent_${cap}.crt"
  local key="$dir/dry-agent_${cap}.key"

  if [[ ! -f "$crt" || ! -f "$key" ]]; then
    echo "Issuing cert for dry-agent ${cap} (expires ${TLS_EXPIRES}) ..."
    step certificate create "dry-agent ${cap}" \
      "$crt" \
      "$key" \
      --ca "$CERT_DIR_CA/dry-agent-root.crt" \
      --ca-key "$CERT_DIR_CA/dry-agent-root.key" \
      --not-after "$TLS_EXPIRES" \
      --san 127.0.0.1 \
      --san localhost \
      --no-password \
      --insecure
  else
    echo "Cert for dry-agent ${cap} already exists, skipping"
  fi
}

traefik_cert() {
  local service="traefik"
  local dir="$CERT_BASE_DIR/$service"
  local crt="$dir/dry-agent_${service^}.crt"
  local key="$dir/dry-agent_${service^}.key"

  if [[ ! -f "$crt" || ! -f "$key" ]]; then
    echo "Issuing cert for dry-agent ${service^} (expires ${TLS_EXPIRES}) ..."
    step certificate create "${PUBLIC_HOST}" \
      "$crt" \
      "$key" \
      --ca "$CERT_DIR_CA/dry-agent-root.crt" \
      --ca-key "$CERT_DIR_CA/dry-agent-root.key" \
      --not-after "$TLS_EXPIRES" \
      --no-password \
      --insecure
  else
    echo "Cert for dry-agent ${service^} already exists, skipping"
  fi
}

# Issue cert for Traefik
traefik_cert "${PUBLIC_HOST}"
cp -f "$CERT_DIR_CA/dry-agent-root.crt" "$CERT_BASE_DIR/traefik/"

# Issue certs for all services
for srv in "${SERVICES[@]}"; do
  issue_cert "$srv"
done

# Copy the Root CA into each service’s directory
for srv in "${SERVICES[@]}"; do
  cp -f "$CERT_DIR_CA/dry-agent-root.crt" "$CERT_BASE_DIR/$srv/"
done
