#!/usr/bin/env bash
# Guard (T-1020): `.env` must be readable the same way by BOTH consumers.
#
#   1. `set -a; . ./.env` — every script/runbook in STATE.md + docs/handover uses this;
#   2. python-dotenv / pydantic-settings (`ConfigService`) and Docker Compose `env_file`.
#
# A value holding a quote, space or shell metacharacter (e.g. a generated password) silently
# breaks (1) — `bash: .env: unexpected EOF` — or, worse, parses to a *different* string than the
# app sees. This script fails loudly instead, and prints only KEY NAMES, never values.
#
# Usage: ./scripts/check_env.sh [path]   (default .env)        exit 0 = both readers agree
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${1:-$ROOT/.env}"
[[ -f "$ENV_FILE" ]] || { echo "✗ $ENV_FILE not found (cp .env.example .env)" >&2; exit 1; }

# 1. shell-sourceable?
if ! err="$(bash -c "set -a; . '$ENV_FILE'" 2>&1)"; then
  echo "✗ $ENV_FILE is not shell-sourceable — scripts using 'set -a; . ./.env' will break:" >&2
  echo "  $err" >&2
  echo "  fix: quote the value, e.g. KEY='v4l!ue\"with specials'" >&2
  exit 1
fi

# 2. same keys AND same values in both readers (names only on mismatch)
"$ROOT/.venv/bin/python" - "$ENV_FILE" <<'PY'
import subprocess
import sys

from dotenv import dotenv_values

path = sys.argv[1]
dot = {k: v for k, v in dotenv_values(path).items() if v is not None}
shell = subprocess.run(
    ["bash", "-c", f"set -a; . '{path}'; set +a; env -0"],
    capture_output=True, text=True, check=True,
).stdout
env = dict(p.split("=", 1) for p in shell.split("\0") if "=" in p)

missing = sorted(k for k in dot if k not in env)
differs = sorted(k for k, v in dot.items() if k in env and env[k] != v)
if missing or differs:
    if missing:
        print(f"✗ keys dotenv sees but the shell does not: {missing}", file=sys.stderr)
    if differs:
        print(f"✗ keys parsed differently by shell vs dotenv: {differs}", file=sys.stderr)
        print("  fix: quote the value in .env (single quotes keep it literal)", file=sys.stderr)
    raise SystemExit(1)
print(f"✓ {len(dot)} keys parse identically for shell, dotenv and Compose env_file")
PY
