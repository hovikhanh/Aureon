"""TC-SYS-003 — the spec parser reads 10-API-SPECIFICATION.md faithfully and fails loudly.

Exercises the public API of `spec_index`:
  * `spec_endpoints()` -> tuple[SpecEndpoint, ...] parsed from §1.10 + per-EP detail sections,
  * `SpecEndpoint` dataclass fields (ep_id/method/path/roles/extra_principal/role_text/paginated)
    and the `.public` property,
  * `role_key_to_code()` -> {role key: ROLE-xx} from §1.4,
  * `parse_role_list()` role-grammar helper,
  * `SpecParseError` raised on a malformed index row (fed through a throwaway spec file, so the
    real 10-API-SPECIFICATION.md is never touched).
"""

from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from tests.contract import spec_index
from tests.contract.spec_index import (
    SpecEndpoint,
    SpecParseError,
    parse_role_list,
    role_key_to_code,
    spec_endpoints,
)

pytestmark = pytest.mark.contract


def test_parses_at_least_35_endpoint_rows() -> None:
    eps = spec_endpoints()
    assert len(eps) >= 35, f"expected >= 35 EP rows in 10 §1.10, parsed {len(eps)}"
    assert all(isinstance(e, SpecEndpoint) for e in eps), "spec_endpoints() must yield SpecEndpoint"
    ids = [e.ep_id for e in eps]
    assert len(set(ids)) == len(ids), f"duplicate EP ids parsed: {ids}"


def test_ep01_is_public_health() -> None:
    ep01 = {e.ep_id: e for e in spec_endpoints()}["EP-01"]
    assert ep01.method == "GET", f"EP-01 method {ep01.method!r} != GET"
    assert ep01.path == "/api/v1/health", f"EP-01 path {ep01.path!r} != /api/v1/health"
    assert ep01.public is True, "EP-01 must be public (DEC-080)"
    assert ep01.roles is None, f"public EP-01 must have roles=None, got {ep01.roles!r}"


def test_ep02_is_public() -> None:
    ep02 = {e.ep_id: e for e in spec_endpoints()}["EP-02"]
    assert ep02.public is True, "EP-02 (login) must be public (DEC-080)"
    assert ep02.method == "POST", f"EP-02 method {ep02.method!r} != POST"
    assert ep02.path == "/api/v1/auth/login", f"EP-02 path {ep02.path!r} != /api/v1/auth/login"


def test_known_rows_method_path_roles_match_spec() -> None:
    by_id = {e.ep_id: e for e in spec_endpoints()}

    ep03 = by_id["EP-03"]
    assert (ep03.method, ep03.path) == ("GET", "/api/v1/auth/me"), f"EP-03 route wrong: {ep03}"
    assert ep03.roles == frozenset({f"ROLE-{n:02d}" for n in range(1, 6)}), (
        f"EP-03 roles {sorted(ep03.roles or [])} != ROLE-01..05 (10 §1.10)"
    )

    ep26 = by_id["EP-26"]
    assert (ep26.method, ep26.path) == ("GET", "/api/v1/documents/{id}/extraction"), (
        f"EP-26 route wrong: {ep26}"
    )
    assert ep26.roles == frozenset({"ROLE-01", "ROLE-02", "ROLE-04", "ROLE-05"}), (
        f"EP-26 roles {sorted(ep26.roles or [])} != ROLE-01, 02, 04, 05 (10 §1.10)"
    )

    ep52 = by_id["EP-52"]
    assert (ep52.method, ep52.path) == ("GET", "/api/v1/audit-logs"), f"EP-52 route wrong: {ep52}"
    assert ep52.roles == frozenset({"ROLE-01"}), (
        f"EP-52 roles {sorted(ep52.roles or [])} != ROLE-01 (10 §1.10)"
    )


def test_extra_principal_detected_for_ep34() -> None:
    ep34 = {e.ep_id: e for e in spec_endpoints()}["EP-34"]
    assert ep34.extra_principal is True, (
        f"EP-34 role cell {ep34.role_text!r} adds a non-role principal (+ người upload): "
        "extra_principal must be True"
    )
    assert ep34.roles == frozenset({"ROLE-02", "ROLE-04", "ROLE-05"}), (
        f"EP-34 base roles {sorted(ep34.roles or [])} != ROLE-02, 04, 05"
    )


def test_role_key_to_code_maps_five_roles_from_section_1_4() -> None:
    mapping = role_key_to_code()
    assert mapping == {
        "CEO": "ROLE-01",
        "CFO": "ROLE-02",
        "SALES_DIRECTOR": "ROLE-03",
        "HR_MANAGER": "ROLE-04",
        "REVIEWER": "ROLE-05",
    }, f"10 §1.4 role-key mapping drifted: {mapping}"


def test_parse_role_list_grammar() -> None:
    assert parse_role_list("Public") is None, "`Public` has no ROLE token -> None"
    assert parse_role_list("ROLE-01..05") == frozenset({f"ROLE-{n:02d}" for n in range(1, 6)}), (
        "range `ROLE-01..05` must expand to all five roles"
    )
    assert parse_role_list("ROLE-01, 02, 04, 05") == frozenset(
        {"ROLE-01", "ROLE-02", "ROLE-04", "ROLE-05"}
    ), "comma list with implicit ROLE- prefix must parse"
    assert parse_role_list("ROLE-02") == frozenset({"ROLE-02"}), "single role must parse"


def _write_spec(tmp_path: Path, index_rows: str, detail: str) -> Path:
    """Build a minimal but structurally valid 10-API-SPECIFICATION.md stand-in."""
    content = (
        "## 1. Quy ước chung\n\n"
        "### 1.4. Xác thực (JWT)\n\n"
        "| Phân quyền | `roles.key` "
        "(`CEO`, `CFO`, `SALES_DIRECTOR`, `HR_MANAGER`, `REVIEWER`) |\n\n"
        "### 1.5. Phân trang\n\n"
        "### 1.10. Danh mục endpoint\n\n"
        "| EP | Method | Path | Nhóm | Role |\n"
        "|---|---|---|---|---|\n"
        f"{index_rows}"
        "\n## 2. Chi tiết\n\n"
        f"{detail}"
    )
    path = tmp_path / "10-API-SPECIFICATION.md"
    path.write_text(content, encoding="utf-8")
    return path


def _clear_caches() -> None:
    spec_index.role_key_to_code.cache_clear()
    spec_index.spec_detail_sections.cache_clear()
    spec_index.spec_endpoints.cache_clear()


@pytest.fixture
def repoint_spec(monkeypatch: pytest.MonkeyPatch) -> Iterator[Callable[[Path], None]]:
    """Yield a hook that aims the parser at a throwaway spec file and drops the @cache memoisation.

    Caches are cleared before (so the throwaway file is read) and after (so later tests see the
    real 10-API-SPECIFICATION.md again).
    """

    def repoint(path: Path) -> None:
        monkeypatch.setattr(spec_index, "API_SPEC", path)
        _clear_caches()

    yield repoint
    _clear_caches()


def test_well_formed_throwaway_spec_parses(
    tmp_path: Path, repoint_spec: Callable[[Path], None]
) -> None:
    index_rows = "| EP-01 | GET | `/health` | Hệ thống | Public |\n"
    detail = (
        "### EP-01 — Health check\n\n"
        "| Method / Path | `GET /api/v1/health` |\n"
        "| Response 200 | envelope |\n\n"
    )
    repoint_spec(_write_spec(tmp_path, index_rows, detail))
    eps = spec_endpoints()
    assert len(eps) == 1 and eps[0].ep_id == "EP-01" and eps[0].public, (
        f"control: well-formed throwaway spec must parse one public EP-01, got {eps}"
    )


def test_malformed_row_raises_spec_parse_error(
    tmp_path: Path, repoint_spec: Callable[[Path], None]
) -> None:
    # A data row that opens with `| EP-` but is missing the backtick-quoted Path cell: unparseable.
    index_rows = "| EP-01 | GET | /health | Hệ thống | Public |\n"
    detail = (
        "### EP-01 — Health check\n\n"
        "| Method / Path | `GET /api/v1/health` |\n"
        "| Response 200 | envelope |\n\n"
    )
    repoint_spec(_write_spec(tmp_path, index_rows, detail))
    with pytest.raises(SpecParseError) as exc:
        spec_endpoints()
    assert "unparseable endpoint index row" in str(exc.value), (
        f"SpecParseError must name the offending row, got: {exc.value}"
    )


def test_bad_role_range_raises_spec_parse_error() -> None:
    # The role grammar helper rejects an out-of-range role (only ROLE-01..05 exist, 10 §1.4).
    with pytest.raises(SpecParseError) as exc:
        parse_role_list("ROLE-01..09")
    assert "out of ROLE-01..05" in str(exc.value), (
        f"parse_role_list must reject ROLE-01..09, got: {exc.value}"
    )
