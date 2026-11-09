"""Intent pre-selection for a chat turn (D-19) — fewer prompt tokens on a CPU-only host.

The full CEO catalog is 16 tool definitions, ~1 300 prompt tokens: 50 s of prompt evaluation for
a 3B model on the demo host before the first output token (measured 2026-11-09). Most demo
questions name their domain ("doanh thu", "nhân sự", "OKR"), so the turn only needs a few tools.

`select_tools` maps the question (diacritics folded, whole-word phrases) to intents. Each intent
names the tools it needs and the READ tools without required arguments that are obviously needed
(`prefetch`, e.g. the pillar dashboard of "doanh thu"). The chat service

* runs the `prefetch` tools through `ToolExecutor` with the asker's Principal before the first
  model round, exactly as if the model had called them (same audit log, same sources) — so a
  typical question takes one model round instead of two;
* advertises only the tools of the matched intents ∩ the tools the asker may see (P06 is applied
  first, this only narrows). An intent already served by a prefetched card advertises nothing
  more: "Doanh thu Q3?" is answered from the finance card with no tool definitions in the prompt.

Nothing here decides an answer: no match → the full permitted catalog and no prefetch (the model
chooses, as before). A write intent ("giao việc") never prefetches. Rule-based, deterministic and
cheap — the model's own tool choice on the full catalog was both slower and worse on the small
local models (measured: 1.5B answered "need more information" instead of calling a tool).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.ai.services.demo_replay import normalise


@dataclass(frozen=True)
class Intent:
    code: str
    phrases: tuple[str, ...]  # folded (no diacritics), matched as whole words
    tools: tuple[str, ...]
    prefetch: tuple[str, ...] = ()
    write: bool = False
    fallback_only: bool = False  # used only when no other intent matched


INTENTS: tuple[Intent, ...] = (
    Intent("finance",
           ("doanh thu", "tai chinh", "dong tien", "loi nhuan", "bien loi nhuan", "chi phi",
            "runway", "cong no", "thu chi", "ngan sach", "tien mat", "revenue", "cash", "margin",
            "finance", "profit", "budget", "expense"),
           ("TOOL-get_finance_dashboard", "TOOL-get_metric", "TOOL-get_lineage"),
           ("TOOL-get_finance_dashboard",)),
    Intent("sales",
           ("ban hang", "doanh so", "pipeline", "khach hang", "co hoi", "chot don", "sales",
            "customer", "customers", "deal", "deals"),
           ("TOOL-get_sales_dashboard", "TOOL-get_metric"), ("TOOL-get_sales_dashboard",)),
    Intent("hr",
           ("nhan su", "tuyen dung", "nghi viec", "nhan vien", "bien che", "headcount", "hr",
            "hiring", "turnover", "people"),
           ("TOOL-get_hr_dashboard", "TOOL-get_org_tree", "TOOL-get_metric"),
           ("TOOL-get_hr_dashboard",)),
    Intent("execution",
           ("cong viec", "du an", "tien do", "qua han", "tre han", "van hanh", "task", "tasks",
            "project", "projects", "overdue"),
           ("TOOL-get_execution_dashboard", "TOOL-get_project_status", "TOOL-list_tasks"),
           ("TOOL-get_execution_dashboard",)),
    Intent("goals",
           ("okr", "kpi", "muc tieu", "ket qua then chot", "goal", "goals", "target", "targets"),
           ("TOOL-get_okr_status", "TOOL-get_kpi_status")),
    Intent("alerts",
           ("canh bao", "rui ro", "bat thuong", "alert", "alerts", "risk", "risks"),
           ("TOOL-list_alerts",), ("TOOL-list_alerts",)),
    Intent("documents",
           ("tai lieu", "quy trinh", "chinh sach", "quy dinh", "hop dong", "sop", "policy",
            "document", "documents", "contract"),
           ("TOOL-search_documents", "TOOL-get_source_document")),
    Intent("lineage", ("nguon goc", "lineage", "tu dau ra"),
           ("TOOL-get_lineage", "TOOL-get_metric")),
    Intent("task_write",
           ("giao viec", "tao task", "tao viec", "giao cho", "nhac viec", "task cho", "assign",
            "create task", "lam giup"),
           ("TOOL-create_task", "TOOL-list_tasks", "TOOL-execute_recommendation"), write=True),
    Intent("decision", ("ghi nhan quyet dinh", "ghi quyet dinh", "record decision"),
           ("TOOL-record_decision",), write=True),
    Intent("overview",
           ("tinh hinh", "tong quan", "cong ty", "toan canh", "suc khoe", "overview", "company"),
           ("TOOL-get_finance_dashboard", "TOOL-get_sales_dashboard", "TOOL-get_hr_dashboard",
            "TOOL-get_execution_dashboard", "TOOL-list_alerts"),
           ("TOOL-get_finance_dashboard", "TOOL-get_sales_dashboard", "TOOL-list_alerts"),
           fallback_only=True),
)  # fmt: skip


@dataclass(frozen=True)
class Selection:
    intents: tuple[str, ...]
    tools: tuple[str, ...] | None  # advertised to the model; None → full permitted catalog
    prefetch: tuple[str, ...]  # READ tools the server runs first (permitted, argument-free)


def _has(text: str, phrase: str) -> bool:
    return f" {phrase} " in f" {text} "


def select_tools(question: str, advertised: list[str]) -> Selection:
    """Tools for this question, in the advertised (registry) order — a stable prompt prefix keeps
    the local model's prompt cache warm. `prefetch` ⊆ the selected tools; empty for writes."""
    text = normalise(question)
    hits = [i for i in INTENTS if not i.fallback_only and any(_has(text, p) for p in i.phrases)]
    if not hits:
        hits = [i for i in INTENTS if i.fallback_only and any(_has(text, p) for p in i.phrases)]
    if not hits:
        return Selection((), None, ())
    codes = tuple(i.code for i in hits)
    wanted = {t for i in hits for t in i.tools}
    tools = tuple(t for t in advertised if t in wanted)
    if not tools:  # nothing the asker may use matches: let the model see what they may use
        return Selection(codes, None, ())
    if any(i.write for i in hits):
        return Selection(codes, tools, ())
    pre = tuple(dict.fromkeys(t for i in hits for t in i.prefetch if t in tools))
    if not pre:
        return Selection(codes, tools, ())
    # The prefetched card already answers an intent that has one: its other tools would only cost
    # prompt tokens (~70 per definition). Intents without a prefetch keep their tools.
    served = {i.code for i in hits if any(t in pre for t in i.prefetch)}
    rest = {t for i in hits if i.code not in served for t in i.tools}
    return Selection(codes, tuple(t for t in advertised if t in rest and t not in pre), pre)
