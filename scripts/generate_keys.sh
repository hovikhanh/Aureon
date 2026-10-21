#!/usr/bin/env bash
# Generate the RS256 key pair for JWT (DEC-129). Output dir is gitignored.
# Usage: scripts/generate_keys.sh [out_dir]   (default: ./secrets — CLAUDE.md §4.2)
set -euo pipefail
OUT="${1:-secrets}"
mkdir -p "$OUT"
chmod 700 "$OUT" 2>/dev/null || echo "warning: cannot chmod $OUT (owned by another user?)" >&2
if [[ -e "$OUT/jwt_private.pem" ]]; then
  echo "refusing to overwrite $OUT/jwt_private.pem (rotate keys manually with a new JWT_KEY_ID)" >&2
  exit 1
fi
openssl genrsa -out "$OUT/jwt_private.pem" 4096
openssl rsa -in "$OUT/jwt_private.pem" -pubout -out "$OUT/jwt_public.pem"
chmod 600 "$OUT/jwt_private.pem"
chmod 644 "$OUT/jwt_public.pem"
echo "wrote $OUT/jwt_private.pem and $OUT/jwt_public.pem"
