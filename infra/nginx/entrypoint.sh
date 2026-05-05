#!/bin/sh
set -e

CERT_DIR=/etc/nginx/certs
KEY="$CERT_DIR/localhost.key"
CRT="$CERT_DIR/localhost.crt"

if [ ! -f "$CRT" ] || [ ! -f "$KEY" ]; then
  echo "[nginx] Generating self-signed certificate..."
  mkdir -p "$CERT_DIR"
  openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "$KEY" \
    -out "$CRT" \
    -subj "/C=BR/ST=SP/L=SaoPaulo/O=MuniAI/CN=localhost"
  echo "[nginx] Certificate generated."
fi

exec nginx -g 'daemon off;'
