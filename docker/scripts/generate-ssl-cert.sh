#!/bin/bash
# Generate a self-signed SSL certificate for nginx if one doesn't exist.
set -euo pipefail

SSL_DIR="/etc/nginx/ssl"
CERT="$SSL_DIR/cmds2.crt"
KEY="$SSL_DIR/cmds2.key"

if [[ -f "$CERT" && -f "$KEY" ]]; then
  echo "[ssl] Certificate already exists, skipping generation."
  exit 0
fi

mkdir -p "$SSL_DIR"

openssl req -x509 -nodes -days 3650 \
  -newkey rsa:2048 \
  -keyout "$KEY" \
  -out "$CERT" \
  -subj "/CN=cmds2-server/O=CMDS2/C=US" \
  2>/dev/null

chmod 640 "$KEY"
echo "[ssl] Self-signed certificate generated: $CERT"
