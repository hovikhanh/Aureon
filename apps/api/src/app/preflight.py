"""Container start preflight: `python -m app.preflight && <command>` (api, celery worker, beat).

Why: after a Windows restart Docker Desktop starts `restart: unless-stopped` containers before the
WSL2 distro's filesystem is available. The bind mounts (`./keys`, `./var/idp-storage`) then come up
as empty, root-owned directories; the API still answers `/health` but every login fails with 500
("JWT public key missing"). Exiting non-zero here lets the restart policy start the container again
— mounts are re-made on every start — until the host files are really there.

Checks (no secret is printed, only names):
1. the JWT key pair is readable (`JWT_*_KEY` env or the `*_KEY_PATH` files);
2. the IDP storage directory exists and is writable by this user;
3. Postgres accepts TCP connections (waits up to `PREFLIGHT_DB_WAIT_S`, default 90 s).
"""

from __future__ import annotations

import os
import socket
import sys
import tempfile
import time
from urllib.parse import urlsplit

from app.core.config import get_config
from app.core.security import load_keys


def check_keys() -> str | None:
    try:
        load_keys(get_config(), need_private=True)
    except (RuntimeError, ValueError, OSError) as exc:
        return f"JWT signing keys unreadable ({type(exc).__name__}): {exc}"
    return None


def check_storage() -> str | None:
    root = get_config().idp_storage_dir
    if not root.is_dir():
        return f"IDP storage directory missing: {root}"
    try:
        with tempfile.NamedTemporaryFile(dir=root, prefix=".preflight-"):
            pass
    except OSError as exc:
        return f"IDP storage directory not writable: {root} ({exc.strerror})"
    return None


def db_endpoint() -> tuple[str, int]:
    parts = urlsplit(get_config().database_url.get_secret_value())
    return parts.hostname or "localhost", parts.port or 5432


def wait_for_db(timeout_s: float) -> str | None:
    host, port = db_endpoint()
    deadline = time.monotonic() + timeout_s
    while True:
        try:
            with socket.create_connection((host, port), timeout=3):
                return None
        except OSError as exc:
            if time.monotonic() >= deadline:
                return f"database {host}:{port} not reachable after {timeout_s:.0f} s ({exc})"
            time.sleep(2)


def main() -> int:
    problems = [p for p in (check_keys(), check_storage()) if p]
    if not problems:
        problem = wait_for_db(float(os.environ.get("PREFLIGHT_DB_WAIT_S", "90")))
        problems += [problem] if problem else []
    for p in problems:
        print(f"PREFLIGHT FAILED: {p}", file=sys.stderr)
    if problems:
        print(
            "PREFLIGHT: exiting so Docker restarts this container (on Docker Desktop + WSL2 the "
            "bind mounts are empty until the distro is up). If it keeps failing, see README "
            "'Troubleshooting'.",
            file=sys.stderr,
        )
        return 1
    print("PREFLIGHT ok: keys, storage, database")
    return 0


if __name__ == "__main__":
    sys.exit(main())
