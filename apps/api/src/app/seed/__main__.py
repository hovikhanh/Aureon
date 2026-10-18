"""``uv run python -m app.seed`` (DEC-062). Exit 1 with a clear message on SeedError."""

from __future__ import annotations

import sys

from app.seed import SeedError, run


def main() -> int:
    try:
        run()
    except SeedError as exc:
        print(f"Seed failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
