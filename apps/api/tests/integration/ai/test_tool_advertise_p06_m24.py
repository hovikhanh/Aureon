"""TC-M24-02 — P06 tool advertisement gate (R-DEC-106, 02 §7.2, 5.5): the tools sent to the model
are filtered by the ASKER's `permissions[]` before the turn. Advertisement is scope-specific, not
a simple role hierarchy (e.g. a DIR who holds `finance:write` is advertised the finance write tools
the CEO is not). A tool is never advertised to an asker lacking any of its `required_permissions`;
write tools demand `ai:write`; frozen P1 tools are never advertised. No new TOOL-* is added — the
existing READ tools already cover Finance/Sales/HR/KPI/OKR/Projects/Risk (R-DEC-106).
"""

import pytest

from app.modules.ai.tools import all_tools
from app.modules.ai.tools.registry import (
    CLASSIFICATION_RANK,
    advertisable_for,
    available_for,
)
from app.modules.auth.permission_matrix import ROLE_PERMISSIONS

pytestmark = pytest.mark.integration

TOTAL_TOOLS = 54  # frozen count (M3.2 +TOOL-execute_recommendation, 10 §7.2.9 + R-DEC-127)


def _perms(role: str) -> frozenset[str]:
    return frozenset(ROLE_PERMISSIONS[role])


def test_no_new_tool_added_by_m24() -> None:
    assert len(all_tools()) == TOTAL_TOOLS, "M2.4 must not add TOOL-* (R-DEC-106)"


def test_advertisement_is_a_subset_of_what_the_asker_may_use() -> None:
    # the gate (P06) only ever narrows `available_for`; it never advertises a tool the asker
    # lacks permission for.
    for role in ("CEO", "DIR", "MGR", "EMP"):
        perms = _perms(role)
        avail = {t.name for t in available_for(perms)}
        adv = {t.name for t in advertisable_for(perms)}
        assert adv <= avail, f"{role}: advertised must be ⊆ available"
        assert adv, f"{role}: at least some tools are advertised"


def test_every_advertised_tool_passes_the_four_p06_conditions() -> None:
    perms = _perms("CEO")
    ceiling = CLASSIFICATION_RANK["SECRET"]
    for t in advertisable_for(perms):
        assert set(t.required_permissions) <= perms  # holds all required perms
        assert t.declare_to_model and not t.p1_frozen  # declarable, not frozen
        assert CLASSIFICATION_RANK[t.data_classification] <= ceiling


def test_finance_tool_not_advertised_without_finance_permission() -> None:
    # TOOL-get_finance_dashboard needs finance:query — an EMP (no finance:*) must not see it.
    emp = {t.name for t in advertisable_for(_perms("EMP"))}
    assert "TOOL-get_finance_dashboard" not in emp
    fin = frozenset({"ai:read", "finance:query"})
    assert "TOOL-get_finance_dashboard" in {t.name for t in advertisable_for(fin)}


def test_available_for_requires_all_required_permissions() -> None:
    # a WRITE tool needs BOTH ai:write and its domain perm — holding only one → not available.
    only_domain = frozenset({"execution:write"})  # lacks ai:write
    assert "TOOL-create_task" not in {t.name for t in available_for(only_domain)}
    only_ai = frozenset({"ai:write"})  # lacks execution:write
    assert "TOOL-create_task" not in {t.name for t in available_for(only_ai)}
    both = frozenset({"ai:write", "execution:write"})
    assert "TOOL-create_task" in {t.name for t in available_for(both)}


def test_write_tools_all_require_ai_write() -> None:
    for t in all_tools():
        if t.kind == "WRITE":
            assert "ai:write" in t.required_permissions, f"{t.name} must require ai:write"
            # and at least one more (domain) permission — never ai:write alone
            assert len(t.required_permissions) >= 2, f"{t.name} must gate on a domain perm too"


def test_frozen_p1_tools_are_never_advertised() -> None:
    # product / risk tools are p1_frozen (R-DEC-16) → never sent to the model, even to the CEO
    advertised = {t.name for t in advertisable_for(_perms("CEO"))}
    frozen = {t.name for t in all_tools() if t.p1_frozen}
    assert frozen and frozen.isdisjoint(advertised)
