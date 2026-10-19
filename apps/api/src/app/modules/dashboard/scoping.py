"""Role × pillar × metric scoping for the dashboard (03 §5.1, 02 §3).

A single source of truth used by EP-10..EP-17 to decide which metrics a role sees,
at which access level (FULL vs AGG), and which alerts it may receive / act on.
"""

from __future__ import annotations

from typing import Literal

AccessLevel = Literal["FULL", "AGG"]

PILLARS: tuple[str, ...] = ("FIN", "CUS", "OPS", "HR")

# metric_code -> access level per role (03 §5.1). Only listed metrics are visible.
# ROLE-01 CEO: everything FULL. ROLE-05 Reviewer: nothing (403 at endpoint).
_FIN = [f"METRIC-FIN-0{i}" for i in range(1, 7)]
_CUS = [f"METRIC-CUS-0{i}" for i in range(1, 6)]
_OPS = [f"METRIC-OPS-0{i}" for i in range(1, 5)]
_HR = [f"METRIC-HR-0{i}" for i in range(1, 4)]


def _full(codes: list[str]) -> dict[str, AccessLevel]:
    return {c: "FULL" for c in codes}


def _agg(codes: list[str]) -> dict[str, AccessLevel]:
    return {c: "AGG" for c in codes}


METRIC_SCOPE: dict[str, dict[str, AccessLevel]] = {
    "ROLE-01": {**_full(_FIN), **_full(_CUS), **_full(_OPS), **_full(_HR)},
    "ROLE-02": {**_full(_FIN), **_full(_OPS), **_agg(_CUS), **_agg(_HR)},
    # Sales Director: FIN only METRIC-FIN-01 (FULL), all CUS FULL, OPS AGG, no HR.
    "ROLE-03": {"METRIC-FIN-01": "FULL", **_full(_CUS), **_agg(_OPS)},
    # HR Manager: FIN only revenue total as AGG (serves HR-01), all OPS FULL, all HR FULL, no CUS.
    "ROLE-04": {"METRIC-FIN-01": "AGG", **_full(_OPS), **_full(_HR)},
    "ROLE-05": {},
}

# Which alert pillars a role receives on the dashboard (02 §3.3, 03 §3.2).
ALERT_RECIPIENT_PILLARS: dict[str, set[str]] = {
    "ROLE-01": {"FIN", "CUS", "OPS", "HR"},
    "ROLE-02": {"FIN", "OPS"},
    "ROLE-03": {"CUS"},
    "ROLE-04": {"HR"},
    "ROLE-05": set(),
}

# Which alert pillars a role may acknowledge / dismiss (02 §3.3; ROLE-02 views OPS but can't ack).
ALERT_ACK_PILLARS: dict[str, set[str]] = {
    "ROLE-01": {"FIN", "CUS", "OPS", "HR"},
    "ROLE-02": {"FIN"},
    "ROLE-03": {"CUS"},
    "ROLE-04": {"HR"},
    "ROLE-05": set(),
}


def visible_metric_codes(role_code: str) -> dict[str, AccessLevel]:
    """Return {metric_code: access_level} for a role (empty for ROLE-05)."""
    return METRIC_SCOPE.get(role_code, {})


def metric_access(role_code: str, metric_code: str) -> AccessLevel | None:
    """Access level for one metric, or None when out of scope."""
    return METRIC_SCOPE.get(role_code, {}).get(metric_code)


def visible_pillars(role_code: str) -> list[str]:
    """Pillars that have at least one visible metric, in canonical order."""
    scope = visible_metric_codes(role_code)
    seen = {code.rsplit("-", 1)[0].replace("METRIC-", "") for code in scope}
    return [p for p in PILLARS if p in seen]


def receives_alert_pillar(role_code: str, pillar: str) -> bool:
    return pillar in ALERT_RECIPIENT_PILLARS.get(role_code, set())


def can_act_alert_pillar(role_code: str, pillar: str) -> bool:
    return pillar in ALERT_ACK_PILLARS.get(role_code, set())
