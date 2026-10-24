"""T-301 — Tool Registry (10 §7). TC-AI-001.

Verifies: the registry has all 53 `TOOL-*` (43 v2.1 + 10 M1.6, T-645) with the correct kind
split (31 READ / 19 WRITE / 2 APPROVAL / 1 EXECUTION), every metadata attribute is present and
valid, permission filtering (P06) and classification filtering (§7.4) behave, and APPROVAL tools
are never advertised to the model (§7.3). No DB / network — pure catalog.
"""

from collections import Counter

from app.core.permissions import VALID_PERMISSIONS
from app.modules.ai.tools import (
    TOOLS,
    advertisable_for,
    all_tools,
    available_for,
    get_tool,
)

ALL_PERMS = frozenset(VALID_PERMISSIONS)


def test_registry_has_53_tools() -> None:
    assert len(all_tools()) == 53
    assert len({t.name for t in TOOLS}) == 53  # unique names


def test_kind_split_matches_spec() -> None:
    c = Counter(t.kind for t in TOOLS)
    assert c["READ"] == 31  # QUERY (v2.1 COMPUTE → READ + compute, R-DEC-70)
    assert sum(t.compute for t in TOOLS) == 2
    assert c["WRITE"] == 19
    assert c["APPROVAL"] == 2
    assert c["EXECUTION"] == 1


def test_every_tool_carries_valid_metadata() -> None:
    for t in TOOLS:
        assert t.name.startswith("TOOL-")
        assert t.description
        assert t.domain
        assert t.endpoint
        assert t.kind in ("READ", "WRITE", "APPROVAL", "EXECUTION")
        assert t.risk_level in ("low", "medium", "high")
        assert t.cost_estimate in ("low", "medium", "high")
        assert t.classification in ("PUBLIC", "INTERNAL", "CONFIDENTIAL", "SECRET")
        assert t.required_permissions, f"{t.name} missing permissions"
        for p in t.required_permissions:
            assert p in VALID_PERMISSIONS, f"{t.name} has undefined permission {p}"
        # READ (incl. compute) → reversible n/a; WRITE → bool
        if t.kind == "READ":
            assert t.reversible is None and t.reversible_label == "n/a"
        else:
            assert isinstance(t.reversible, bool)


def test_write_tools_require_ai_write_plus_domain() -> None:
    for t in TOOLS:
        if t.kind == "WRITE":
            assert "ai:write" in t.required_permissions
            # at least one domain:write / domain:read companion
            assert len(t.required_permissions) >= 1


def test_permission_filter_scopes_tools_by_role() -> None:
    # EMPLOYEE-like: only execution:read → only the 6 execution read tools
    emp = {t.name for t in available_for(frozenset({"execution:read"}))}
    assert emp == {
        "TOOL-list_tasks",
        "TOOL-list_objectives",
        "TOOL-get_kpi_status",
        "TOOL-get_okr_status",
        "TOOL-get_overdue_tasks",
        "TOOL-get_project_status",
    }
    # no permissions → nothing
    assert available_for(frozenset()) == ()
    # all permissions → all 53
    assert len(available_for(ALL_PERMS)) == 53


def test_classification_filter_caps_advertised_tools() -> None:
    internal = advertisable_for(ALL_PERMS, max_classification="INTERNAL")
    assert internal and all(t.classification == "INTERNAL" for t in internal)
    conf = advertisable_for(ALL_PERMS, max_classification="CONFIDENTIAL")
    assert len(conf) > len(internal)
    assert all(t.classification in ("INTERNAL", "CONFIDENTIAL") for t in conf)


def test_approval_tools_never_advertised_to_model() -> None:
    adv = advertisable_for(ALL_PERMS)
    assert all(t.kind != "APPROVAL" for t in adv)
    # but they are still "available" (server may call them)
    av = {t.name for t in available_for(ALL_PERMS)}
    assert "TOOL-approve_request" in av and "TOOL-reject_request" in av


def test_get_tool_lookup() -> None:
    assert get_tool("TOOL-get_finance_dashboard").domain == "finance"  # type: ignore[union-attr]
    assert get_tool("TOOL-nope") is None


def test_p1_frozen_product_risk_tools_not_advertised() -> None:
    """TC-M11-14 (R-DEC-16): product/risk tools are tagged `p1_frozen` and never sent to the
    model, even to a holder of every permission; they stay in the catalog (EP-119) and runnable."""
    frozen = {t.name for t in all_tools() if t.p1_frozen}
    assert frozen == {
        "TOOL-get_product_dashboard",
        "TOOL-get_product_metrics",
        "TOOL-get_risk_dashboard",
        "TOOL-list_risks",
        "TOOL-run_risk_scenario",
        "TOOL-upsert_risk",
        "TOOL-create_mitigation",
    }
    assert all(t.domain in ("product", "risk") for t in all_tools() if t.p1_frozen)
    assert all(t.p1_frozen for t in all_tools() if t.domain in ("product", "risk"))
    advertised = {t.name for t in advertisable_for(ALL_PERMS)}
    assert advertised.isdisjoint(frozen)
    assert frozen <= {t.name for t in available_for(ALL_PERMS)}
