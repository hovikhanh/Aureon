"""TC-M5-01 (contract) — every in-app link the backend puts in a notification opens a real page.

Alert notifications linked to `/dashboard/metrics/<code>`; the web middleware 308s v2.1
`/dashboard/*` to `/home/*`, and `/home/metrics/<code>` had no page → 404. Two more links
(`/knowledge/decisions`, `/work/tasks/<id>`) pointed at routes that did not exist either. This test
reads the link templates straight from the backend source and the page tree of `apps/web`, so a
new link (or a moved page) cannot silently break the bell again.
"""

import re
from pathlib import Path

import pytest

from app.core.config import REPO_ROOT

pytestmark = pytest.mark.contract

API_SRC = Path(REPO_ROOT) / "apps" / "api" / "src" / "app"
WEB_APP = Path(REPO_ROOT) / "apps" / "web" / "src" / "app"
LEGACY = Path(REPO_ROOT) / "apps" / "web" / "src" / "lib" / "legacy-routes.ts"

# `link=f"/work?task={t.id}"`, `link = f"/home/metrics/{m.code}"`, `HOME_LINK = "/home"`
LINK = re.compile(r"""(?:\blink\s*=\s*|_LINK\s*=\s*)f?["'](/[^"']*)["']""")


def backend_links() -> dict[str, str]:
    """link template → the source file that emits it (query string dropped)."""
    out: dict[str, str] = {}
    for path in API_SRC.rglob("*.py"):
        for raw in LINK.findall(path.read_text(encoding="utf-8")):
            out[raw.split("?", 1)[0]] = str(path.relative_to(API_SRC))
    return out


def page_patterns() -> list[re.Pattern[str]]:
    """One regex per `page.tsx`: route groups `(x)` vanish, `[param]` matches one segment."""
    patterns = []
    for page in WEB_APP.rglob("page.tsx"):
        parts = [p for p in page.parent.relative_to(WEB_APP).parts if not p.startswith("(")]
        regex = "".join(
            "/[^/]+" if p.startswith("[") and p.endswith("]") else "/" + re.escape(p) for p in parts
        )
        patterns.append(re.compile(f"^{regex or '/'}$"))
    return patterns


def legacy_redirect(path: str) -> str:
    """Mirror of `legacyRedirect()` in `apps/web/src/lib/legacy-routes.ts` (first prefix wins)."""
    pairs = re.findall(r'\["(/[^"]*)",\s*"(/[^"]*)"\]', LEGACY.read_text(encoding="utf-8"))
    for src, dst in pairs:
        if path == src or path.startswith(src + "/"):
            return dst + path[len(src) :]
    return path


def test_backend_notification_links_resolve_to_web_pages() -> None:
    links = backend_links()
    assert links, "no notification link found — the LINK pattern no longer matches the code"
    pages = page_patterns()
    broken = []
    for template, origin in sorted(links.items()):
        concrete = re.sub(r"\{[^}]+\}", "x1", template)  # `{m.code}` → one path segment
        target = legacy_redirect(concrete)
        if not any(p.match(target) for p in pages):
            broken.append(f"{template} (from {origin}) → {target}: no page.tsx")
    assert not broken, "notification links that 404 in the web app:\n  " + "\n  ".join(broken)


def test_the_m5_links_point_at_their_v3_pages() -> None:
    """The three links fixed in M5 keep their v3 targets (not the legacy / missing ones)."""
    links = backend_links()
    assert "/home/metrics/{m.code}" in links
    assert "/dashboard/metrics/{m.code}" not in links
    assert not any(t.startswith("/work/tasks/") for t in links)
    assert "/knowledge/decisions" in links  # served by app/(app)/knowledge/[tab]/page.tsx
