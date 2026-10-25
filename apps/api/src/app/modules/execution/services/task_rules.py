"""Pure task rules (DEC-147, 05 ENT-Task) — 7-status state machine, unit-tested (TC-EXE-003)."""

from collections.abc import Iterable, Mapping
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


# 05 §2.5: `source_ref.kind` must agree with `task_source` (R-DEC-42 sibling rule).
SOURCE_KIND_TASK_SOURCE: dict[str, str] = {
    "meeting": "meeting",
    "decision": "meeting",
    "ai_action": "ai",
    "document": "document",
    "mitigation": "mitigation",
}
MAX_DEPENDENCY_DEPTH = 50  # 05 §2.5 — BFS depth guard


def source_kind_matches(kind: str, task_source: str) -> bool:
    return SOURCE_KIND_TASK_SOURCE.get(kind) == task_source


def find_cycle[K](start: K, target: K, edges: Mapping[K, Iterable[K]]) -> list[K] | None:
    """Adding `target → start` (target depends on start) closes a cycle iff `start` already
    reaches `target` along `depends_on` edges. Returns the path `[target, start, …, target]`.

    Raises `ValueError("depth")` past `MAX_DEPENDENCY_DEPTH` levels (05 §2.5).
    """
    if start == target:
        return [target, target]
    parent: dict[K, K | None] = {start: None}
    frontier, depth = [start], 0
    while frontier:
        depth += 1
        if depth > MAX_DEPENDENCY_DEPTH:
            raise ValueError("depth")
        nxt: list[K] = []
        for node in frontier:
            for dep in edges.get(node, ()):
                if dep in parent:
                    continue
                parent[dep] = node
                if dep == target:
                    path: list[K] = [dep]
                    cur: K | None = node
                    while cur is not None:
                        path.append(cur)
                        cur = parent[cur]
                    return [target, *reversed(path[1:]), target]
                nxt.append(dep)
        frontier = nxt
    return None
