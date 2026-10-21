"""Pure task rules (DEC-147, 05 ENT-Task) — 7-status state machine, unit-tested (TC-EXE-003)."""

from datetime import date

OPEN = frozenset({"backlog", "todo", "in_progress", "blocked", "in_review"})
CLOSED = frozenset({"done", "cancelled"})

TRANSITIONS: dict[str, frozenset[str]] = {
    "backlog": frozenset({"todo", "in_progress", "blocked", "cancelled"}),
    "todo": frozenset({"backlog", "in_progress", "blocked", "done", "cancelled"}),
    "in_progress": frozenset({"todo", "blocked", "in_review", "done", "cancelled"}),
    "blocked": frozenset({"todo", "in_progress", "cancelled"}),
    "in_review": frozenset({"in_progress", "blocked", "done", "cancelled"}),
    "done": frozenset({"in_progress"}),  # reopen
    "cancelled": frozenset({"backlog", "todo"}),  # restore
}


def can_transition(src: str, dst: str) -> bool:
    return src == dst or dst in TRANSITIONS.get(src, frozenset())


def is_overdue(status: str, due: date | None, as_of: date) -> bool:
    return due is not None and status in OPEN and due < as_of
