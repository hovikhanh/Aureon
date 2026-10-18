"""Parse docs/3.EXECUTION/10-API-SPECIFICATION.md at test time (T-009, DEC-101, TC-SYS-003).

Nothing here is hand-copied from 10: the endpoint index (§1.10), the per-endpoint detail sections
(`### EP-xx — ...`) and the role key ↔ code mapping (§1.4) are read from the Markdown each run, so
the contract suite cannot drift from the spec. Any row that cannot be understood raises
`SpecParseError` with the offending line — never a silent pass.

Role-column grammar (§1.10 "Role"):
  * `Public`                                  → public endpoint (DEC-080: only EP-01, EP-02)
  * `ROLE-01..05`, `ROLE-01, 02, 04, 05`, `ROLE-01..04 (theo trụ)`, `ROLE-01..05, chỉ ...`
                                              → role list; parenthesised / trailing text is a note
  * a parenthetical starting with `+` (EP-34 `(+ người upload ...)`) means a non-role principal
    may also call the endpoint → `extra_principal=True` (role gate must be a superset)
  * no ROLE token (EP-36 `Người upload tài liệu đó`) → fall back to `require_role(...)` in the
    endpoint's detail section; if that is missing too → SpecParseError.
"""

import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
API_SPEC = REPO_ROOT / "docs/3.EXECUTION/10-API-SPECIFICATION.md"
BASE_PATH = "/api/v1"
HTTP_METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE"})

_INDEX_ROW = re.compile(
    r"^\| (?P<ep>EP-\d{2}) \| (?P<method>[A-Z]+) \| `(?P<path>/[^`]*)` \| (?P<group>[^|]+) \| "
    r"(?P<role>[^|]+) \|\s*$"
)
_ROLE_ITEM = re.compile(r"(?:ROLE-)?(\d{2})(?:\.\.(?:ROLE-)?(\d{2}))?")
_DETAIL_HEADING = re.compile(r"^### (EP-\d{2}) — ", re.M)
_METHOD_PATH_ROW = re.compile(r"^\| Method / Path \| `(?P<method>[A-Z]+) (?P<path>/[^` ]*)`", re.M)
_ROLE_ROW = re.compile(r"^\| Role \| (?P<role>.+?) \|\s*$", re.M)
_RESPONSE_ROW = re.compile(r"^\| Response (?P<status>\d{3}) \| (?P<text>.+?) \|\s*$", re.M)
_QUERY_ROW = re.compile(r"^\| Query \| (?P<text>.+?) \|\s*$", re.M)


class SpecParseError(AssertionError):
    """10-API-SPECIFICATION.md has a row/section this parser does not understand."""


@dataclass(frozen=True, slots=True)
class SpecEndpoint:
    ep_id: str
    method: str
    path: str  # full path incl. /api/v1
    roles: frozenset[str] | None  # None = public
    extra_principal: bool  # a non-role principal (e.g. uploader) may also call it
    role_text: str  # raw role cell, for error messages
    paginated: bool  # list endpoint with `meta` pagination (10 §1.5)

    @property
    def public(self) -> bool:
        return self.roles is None


def _section(text: str, start: str, end: str) -> str:
    if start not in text or end not in text.split(start, 1)[1]:
        raise SpecParseError(f"10-API-SPECIFICATION.md: section {start!r}..{end!r} not found")
    return text.split(start, 1)[1].split(end, 1)[0]


def parse_role_list(text: str) -> frozenset[str] | None:
    """Parse `ROLE-01..04`, `ROLE-01, 02, 04, 05`, `ROLE-02` → role codes; None if no ROLE token."""
    start = text.find("ROLE-")
    if start < 0:
        return None
    roles: set[str] = set()
    pos = start
    while True:
        m = _ROLE_ITEM.match(text, pos)
        if m is None:
            raise SpecParseError(f"cannot parse role list in {text!r}")
        lo = int(m.group(1))
        hi = int(m.group(2) or lo)
        if not 1 <= lo <= hi <= 5:
            raise SpecParseError(f"role range out of ROLE-01..05 in {text!r}")
        roles.update(f"ROLE-{n:02d}" for n in range(lo, hi + 1))
        sep = re.compile(r"\s*,\s*").match(text, m.end())
        if sep is None or _ROLE_ITEM.match(text, sep.end()) is None:
            return frozenset(roles)
        pos = sep.end()


def _strip_parentheticals(text: str) -> tuple[str, list[str]]:
    notes = re.findall(r"\(([^()]*)\)", text)
    return re.sub(r"\([^()]*\)", "", text), notes


def _detail_sections(text: str) -> dict[str, str]:
    parts = _DETAIL_HEADING.split(text)
    sections: dict[str, str] = {}
    for ep_id, body in zip(parts[1::2], parts[2::2], strict=True):
        if ep_id in sections:
            raise SpecParseError(f"duplicate detail section for {ep_id}")
        # A section ends at the next `## ` heading too.
        sections[ep_id] = re.split(r"^## ", body, maxsplit=1, flags=re.M)[0]
    return sections


def detail_require_roles(section: str) -> frozenset[str] | None:
    m = _ROLE_ROW.search(section)
    if m is None:
        return None
    call = re.search(r"require_role\(([^)]*)\)", m.group("role"))
    return parse_role_list(call.group(1)) if call else None


def _is_paginated(section: str) -> bool:
    texts = [m.group("text") for m in _QUERY_ROW.finditer(section)]
    texts += [m.group("text") for m in _RESPONSE_ROW.finditer(section)]
    return any("phân trang" in t for t in texts)


@cache
def role_key_to_code() -> dict[str, str]:
    """10 §1.4: `ROLE-xx` ↔ `roles.key` (`CEO`, `CFO`, ...) in ROLE-01..05 order."""
    section = _section(API_SPEC.read_text(encoding="utf-8"), "### 1.4.", "### 1.5.")
    m = re.search(r"`roles\.key` \(([^)]*)\)", section)
    if m is None:
        raise SpecParseError("10 §1.4: role key list `roles.key` (...) not found")
    keys = re.findall(r"`([A-Z_]+)`", m.group(1))
    if len(keys) != 5:
        raise SpecParseError(f"10 §1.4: expected 5 role keys, got {keys}")
    return {key: f"ROLE-{i:02d}" for i, key in enumerate(keys, start=1)}


@cache
def spec_detail_sections() -> dict[str, str]:
    return _detail_sections(API_SPEC.read_text(encoding="utf-8"))


@cache
def spec_endpoints() -> tuple[SpecEndpoint, ...]:
    """All rows of 10 §1.10, enriched with detail-section data. Raises on anything unparseable."""
    text = API_SPEC.read_text(encoding="utf-8")
    index = _section(text, "### 1.10.", "\n## ")
    details = spec_detail_sections()
    endpoints: list[SpecEndpoint] = []
    errors: list[str] = []
    for line in index.splitlines():
        if not line.startswith("| EP-"):
            continue
        m = _INDEX_ROW.match(line)
        if m is None:
            errors.append(f"unparseable endpoint index row: {line!r}")
            continue
        ep_id, method, rel_path = m.group("ep"), m.group("method"), m.group("path")
        role_text = m.group("role").strip()
        if method not in HTTP_METHODS:
            errors.append(f"{ep_id}: unknown HTTP method {method!r}")
            continue
        section = details.get(ep_id)
        if section is None:
            errors.append(f"{ep_id}: no `### {ep_id} — ...` detail section")
            continue
        main, notes = _strip_parentheticals(role_text)
        extra_principal = any(n.strip().startswith("+") for n in notes)
        roles: frozenset[str] | None
        try:
            if main.strip() == "Public":
                roles = None
            else:
                roles = parse_role_list(main) or detail_require_roles(section)
                if roles is None:
                    errors.append(
                        f"{ep_id}: role cell {role_text!r} has no ROLE-xx and the detail section "
                        "has no `require_role(...)`"
                    )
                    continue
        except SpecParseError as exc:
            errors.append(f"{ep_id}: {exc}")
            continue
        endpoints.append(
            SpecEndpoint(
                ep_id=ep_id,
                method=method,
                path=BASE_PATH + rel_path,
                roles=roles,
                extra_principal=extra_principal,
                role_text=role_text,
                paginated=_is_paginated(section),
            )
        )
    ids = [e.ep_id for e in endpoints]
    keys = [(e.method, e.path) for e in endpoints]
    errors += [f"duplicate EP id {i}" for i in sorted({i for i in ids if ids.count(i) > 1})]
    errors += [f"duplicate route {k}" for k in sorted({k for k in keys if keys.count(k) > 1})]
    if errors:
        raise SpecParseError("10-API-SPECIFICATION.md §1.10:\n  " + "\n  ".join(errors))
    return tuple(endpoints)


def detail_method_path(ep_id: str) -> tuple[str, str] | None:
    m = _METHOD_PATH_ROW.search(spec_detail_sections()[ep_id])
    return (m.group("method"), m.group("path")) if m else None
