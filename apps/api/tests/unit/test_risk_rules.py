"""TC-RSK-001 — BR-RSK-01/02 pure rules (score, level bands, code, lifecycle)."""

import pytest

from app.modules.risk.services import rules


@pytest.mark.parametrize(
    ("score", "level"),
    [(1, "low"), (4, "low"), (5, "medium"), (9, "medium"), (10, "high"), (15, "high"),
     (16, "critical"), (25, "critical")],
)  # fmt: skip
def test_level_bands(score: int, level: str) -> None:
    assert rules.level_for(score) == level


def test_score_and_bounds() -> None:
    assert rules.risk_score(3, 4) == 12
    assert rules.risk_score(5, 5) == 25
    with pytest.raises(ValueError):
        rules.risk_score(0, 3)
    with pytest.raises(ValueError):
        rules.risk_score(3, 6)
    with pytest.raises(ValueError):
        rules.level_for(26)
    assert rules.owner_required(5) and not rules.owner_required(4)


def test_codes() -> None:
    assert rules.format_code(2037, 7) == "RSK-2037-007"
    assert rules.next_seq(None) == 1
    assert rules.next_seq("RSK-2037-007") == 8
    assert rules.format_code(2037, 1234) == "RSK-2037-1234"


def test_transitions() -> None:
    assert rules.can_transition("proposed", "identified")
    assert rules.can_transition("proposed", "rejected")
    assert not rules.can_transition("proposed", "closed")
    assert rules.can_transition("identified", "closed")
    assert rules.can_transition("monitoring", "mitigating")
    assert not rules.can_transition("closed", "identified")
    assert not rules.can_transition("rejected", "identified")
    assert rules.can_transition("accepted", "closed")
    assert not rules.can_transition("mitigating", "accepted")
    assert len(rules.CATEGORIES) == 13


def test_aggregate_and_pillar() -> None:
    assert rules.aggregate_score([]) is None
    assert rules.aggregate_score([16, 9, 4]) == 9.7
    assert rules.pillar_status([]) == "no_data"
    assert rules.pillar_status(["no_data", "ok"]) == "no_data"
    assert rules.pillar_status(["ok", "warning", "ok"]) == "warning"
    assert rules.pillar_status(["critical", "warning", "ok"]) == "critical"
    assert rules.pillar_status(["ok", "ok"]) == "ok"
