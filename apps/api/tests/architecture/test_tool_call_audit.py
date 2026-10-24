"""T-647 / TC-M16-11 — no tool call path skips the audit log (R-DEC-74).

Every module that runs `ToolExecutor.run(...)` or proposes an AIAction from a tool must log through
`tool_audit.log_tool_call`; `ToolCallLog(...)` is constructed only inside `tool_audit.py`.
"""

import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src" / "app"
AI = SRC / "modules" / "ai" / "services"

# module → why it is a tool-call site (executor.run or a WRITE tool → AIAction card)
CALL_SITES = {
    "chat_service.py": "EP-AI-01/02 chat + SSE (`executor.run`) and demo replay rows",
    "demo_replay.py": "replay runs READ tools; ChatService._finish_replay logs them",
    "action_service.py": "propose() — WRITE tool → AIAction (ai_action_id link)",
}


def _py() -> list[Path]:
    return [p for p in SRC.rglob("*.py") if "__pycache__" not in p.parts]


def test_tool_call_log_built_only_in_tool_audit() -> None:
    offenders = [
        str(p.relative_to(SRC)) for p in _py()
        if re.search(r"\bToolCallLog\(", p.read_text()) and p.name not in ("tool_audit.py",)
        and p.parent.name != "models"
    ]  # fmt: skip
    assert offenders == []


def test_every_executor_call_site_is_known_and_audited() -> None:
    sites = {p.name for p in _py() if re.search(r"\bexecutor\.run\(", p.read_text())}
    assert sites <= set(CALL_SITES), sites - set(CALL_SITES)
    for name in ("chat_service.py", "action_service.py"):
        assert "log_tool_call(" in (AI / name).read_text(), name
