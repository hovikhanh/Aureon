"""Pure BR-RSK rules (03 §5.5) — no I/O, unit-tested exactly, reused by metrics/dashboard.

- BR-RSK-01: `risk_score = likelihood × impact` (1..25); `RSK-YYYY-NNN` code.
- BR-RSK-02: level bands 1–4 low · 5–9 medium · 10–15 high · 16–25 critical; lifecycle
  `proposed → identified → assessed → mitigating → monitoring → closed`, `proposed → rejected`,
  `accepted` only via EP-104 (DEC-216).
"""

from typing import Literal

Level = Literal["low", "medium", "high", "critical"]
LEVELS: tuple[Level, ...] = ("low", "medium", "high", "critical")
LEVEL_RANK = {lvl: i for i, lvl in enumerate(LEVELS)}

CATEGORIES = (
    "financial", "operational", "strategic", "people", "business", "customer", "product",
    "technology", "security", "compliance", "legal", "partner_supplier", "ai",
)  # fmt: skip
STATUSES = (
    "proposed", "identified", "assessed", "mitigating", "monitoring", "accepted", "closed",
    "rejected",
)  # fmt: skip
# Statuses that count as "open" for METRIC-RSK-01..05 and EP-100 (05 §4.6, DEC-148):
# `proposed` / `rejected` never count; `closed` / `accepted` are no longer open.
OPEN_STATUSES = frozenset({"identified", "assessed", "mitigating", "monitoring"})
TERMINAL_STATUSES = frozenset({"closed", "rejected"})
HIGH_LEVELS = frozenset({"high", "critical"})
ACTIVE_MITIGATION = frozenset({"planned", "in_progress"})

_CHAIN = ("identified", "assessed", "mitigating", "monitoring", "closed")
# EP-106 transitions (DEC-216): forward along the chain (skips allowed), `monitoring →
# mitigating` re-opens work, `accepted → closed`; `accepted` itself is EP-104 only.
TRANSITIONS: dict[str, frozenset[str]] = {
    "proposed": frozenset({"identified", "rejected"}),
    **{s: frozenset(_CHAIN[i + 1 :]) for i, s in enumerate(_CHAIN)},
    "accepted": frozenset({"closed"}),
    "rejected": frozenset(),
}
TRANSITIONS["monitoring"] = TRANSITIONS["monitoring"] | {"mitigating"}
OWNER_REQUIRED = frozenset({"identified", "mitigating", "closed"})
MITIGATED_STATUSES = frozenset({"monitoring", "closed"})


def risk_score(likelihood: int, impact: int) -> int:
    if not (1 <= likelihood <= 5 and 1 <= impact <= 5):
        raise ValueError("likelihood and impact must be 1..5")
    return likelihood * impact


def level_for(score: int) -> Level:
    """BR-RSK-02 band of a 1..25 score."""
    if not 1 <= score <= 25:
        raise ValueError("risk_score must be 1..25")
    if score >= 16:
        return "critical"
    if score >= 10:
        return "high"
    return "medium" if score >= 5 else "low"


def owner_required(score: int) -> bool:
    """Manual risks with `risk_score ≥ 5` (medium+) must have an owner (BR-RSK-02)."""
    return score >= 5


def format_code(year: int, seq: int) -> str:
    return f"RSK-{year:04d}-{seq:03d}"


def next_seq(last_code: str | None) -> int:
    """`RSK-2037-007` → 8; `None` → 1."""
    if not last_code:
        return 1
    return int(last_code.rsplit("-", 1)[1]) + 1


def can_transition(current: str, target: str) -> bool:
    return target in TRANSITIONS.get(current, frozenset())


def aggregate_score(scores: list[int]) -> float | None:
    """METRIC-RSK-04 / EP-100: mean score of open risks, 1 decimal; none open → None."""
    if not scores:
        return None
    return round(sum(scores) / len(scores), 1)


def pillar_status(metric_statuses: list[str]) -> str:
    """10 §5: worst metric wins; ≥ 50% `no_data` (or none) → `no_data`."""
    if not metric_statuses or metric_statuses.count("no_data") * 2 >= len(metric_statuses):
        return "no_data"
    for s in ("critical", "warning"):
        if s in metric_statuses:
            return s
    return "ok"


def heatmap(cells: list[tuple[int, int]]) -> list[dict[str, int]]:
    """5×5 likelihood × impact grid (25 cells, zero-filled, likelihood then impact asc)."""
    counts: dict[tuple[int, int], int] = {}
    for cell in cells:
        counts[cell] = counts.get(cell, 0) + 1
    return [
        {"likelihood": li, "impact": im, "count": counts.get((li, im), 0)}
        for li in range(1, 6)
        for im in range(1, 6)
    ]
