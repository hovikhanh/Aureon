"""Proactive insights (T-303, FR-AI-07, 03 §7.1) — the 9-part grounded `ENT-Insight`.

Generation is grounded, not free-form: the numbers in `structured.evidence` come from
`ENT-MetricValue` (via `DashboardService`), never the model (P05, FR-AIQ-01). The gateway writes
only the one-sentence `observation` narration; a grounding validator then drops any insight left
with **zero** evidence (GAP D-15 — unsupported numbers are blocked, not labelled "estimate").

A pillar insight is produced from its worst breaching metric + open alerts. The 9 parts
(03 §7.1) are: root_cause, risk, expected_outcome, action, evidence, confidence, alternatives,
timeline, owner — all required for `kind ∈ {anomaly, risk, recommendation}`.

Reads (EP-114) filter by `audience_roles` **and** pillar scope: an insight whose observation
depends on a pillar the viewer cannot see is hidden, and out-of-scope evidence is dropped.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal
from app.core.model_gateway.types import ChatRequest, ChatResponse
from app.core.model_gateway.types import Message as GwMessage
from app.modules.ai.models import Insight
from app.modules.ai.repositories import InsightRepository
from app.modules.ai.schemas import (
    ConfidenceOut,
    InsightOut,
    RecommendationOut,
    SourceRefOut,
)
from app.modules.ai.services.prompt_guard import wrap_data
from app.modules.dashboard.services.dashboard_service import (
    DashboardService,
    metric_visible,
    visible_pillars,
)

# Pillar owner = the responsible director (R-DEC-12a: 5 C-level nền v2.1 → DIR).
PILLAR_OWNER = {"F": "DIR", "C": "DIR", "O": "DIR", "U": "DIR", "S": "DIR"}
# Roles seeing a pillar's insight: CEO + DIR (pillar narrowing applied via visible_pillars).
PILLAR_AUDIENCE = {
    "F": ["CEO", "DIR"], "C": ["CEO", "DIR"], "O": ["CEO", "DIR"],
    "U": ["CEO", "DIR"], "S": ["CEO", "DIR"],
}  # fmt: skip
INSIGHT_TTL = timedelta(days=7)
REQUIRED_PARTS = (
    "root_cause", "risk", "expected_outcome", "action", "evidence",
    "confidence", "alternatives", "timeline", "owner",
)  # fmt: skip


class GatewayLike(Protocol):
    async def chat(self, req: ChatRequest) -> ChatResponse: ...


@dataclass
class InsightDraft:
    pillar: str
    kind: str
    severity: str
    observation: str
    structured: dict[str, Any]
    evidence: list[dict[str, Any]]


class InsightService:
    def __init__(self, db: AsyncSession, gateway: GatewayLike | None = None) -> None:
        self.db = db
        self.gateway = gateway
        self._dash = DashboardService(db)

    # ---------- generation ----------
    async def generate_for_pillar(self, author: Principal, pillar: str) -> Insight | None:
        """Build one grounded insight for a pillar, or None if there is nothing to report."""
        metrics = await self._dash.metrics(author, pillar=pillar)
        breaching = [m for m in metrics if m.status in ("warning", "critical")]
        if not breaching:
            return None
        worst = max(breaching, key=lambda m: 0 if m.status == "warning" else 1)
        evidence = [
            SourceRefOut(
                type="metric_value",
                id=m.metric_code,
                label=m.metric_code,
                period_key=m.period_key,
                value=m.value,
                lineage_url=m.lineage_url,
            ).model_dump()
            for m in breaching
        ]
        observation = await self._narrate(pillar, worst, evidence)
        kind = "anomaly" if worst.status == "critical" else "recommendation"
        band, reason = self._confidence(breaching)
        structured = {
            "impact": f"{worst.metric_code} ở mức {worst.status} đang kéo sức khỏe trụ "
                      f"{pillar} xuống.",
            "root_cause": "Chưa xác định chắc chắn — cần rà soát bản ghi nguồn.",
            "risk": f"{worst.metric_code} đang ở mức {worst.status}; để kéo dài sẽ ảnh "
                    f"hưởng trụ {pillar}.",
            "expected_outcome": {"metric_id": worst.metric_code, "target": "về ngưỡng",
                                 "by": "+7d"},
            "action": [{"text": f"Rà soát {worst.metric_code}", "tool": "TOOL-create_task"}],
            "evidence": evidence,
            "confidence": {"band": band, "reason": reason},
            "alternatives": ["Không hành động — chấp nhận rủi ro hiện tại."],
            "timeline": "Trong 48 giờ; kiểm tra 24h/7d.",
            "owner": PILLAR_OWNER.get(pillar, "CEO"),
        }  # fmt: skip
        # ENT-Insight.severity uses platform.alert_severity (WARNING|CRITICAL, DEC-231)
        severity = worst.status.upper()
        draft = InsightDraft(pillar, kind, severity, observation, structured, evidence)
        return await self._persist(draft, band)

    async def generate_for_kpi(self, payload: dict[str, Any]) -> Insight | None:
        """A KPI breach (`execution.kpi_below_threshold`) → one 9-part insight with a root cause
        read from the owner's overdue work and an **L2** recommendation (MGR approves a task tied
        to the KPI; never auto-executed — R-DEC-108, UC-03). Grounded on the KPI value itself.
        """
        code = str(payload.get("kpi_code", "KPI"))
        period = str(payload.get("period_key", ""))
        raw_pct = payload.get("achievement_pct")
        if raw_pct is None:
            return None
        try:
            pct = float(raw_pct)
        except (TypeError, ValueError):
            return None
        band_in = str(payload.get("band", "BELOW"))
        kpi_id = str(payload.get("kpi_id", ""))
        overdue = await self._owner_overdue(payload)
        # evidence: the KPI value is the grounded number (GAP D-15 — ≥ 1 SourceRef)
        evidence = [
            SourceRefOut(
                type="metric_value",
                id=code,
                label=f"KPI {code}",
                period_key=period,
                value=pct,
                lineage_url=f"/goals/kpis/{kpi_id}",
            ).model_dump()
        ]
        observation = f"KPI {code} đạt {pct:g}% kỳ {period} — ở mức {band_in}."
        root = (
            f"Phát hiện {overdue} việc quá hạn của người phụ trách — khả năng là nguyên nhân "
            f"trực tiếp kéo KPI xuống." if overdue
            else "Chưa thấy việc quá hạn của người phụ trách; cần rà soát bản ghi nguồn của kỳ."
        )  # fmt: skip
        structured = {
            "impact": f"KPI {code} dưới ngưỡng ảnh hưởng mục tiêu kỳ {period}.",
            "root_cause": root,
            "risk": f"Giữ nguyên {band_in} sẽ làm lệch mục tiêu kỳ và các kỳ kế tiếp.",
            "expected_outcome": {"metric_id": code, "target": "về ngưỡng", "by": "+14d"},
            # L2: a proposed task tied to the KPI — MGR confirms via an ActionCard (not auto-run)
            "action": [{
                "text": f"Giao việc khắc phục KPI {code} (chờ MGR duyệt)",
                "tool": "TOOL-create_task", "autonomy_level": "L2",
                "input": {"kpi_code": code, "kpi_id": kpi_id, "period_key": period},
            }],
            "evidence": evidence,
            "confidence": {"band": "MEDIUM", "reason": "Một chỉ số KPI tươi + tín hiệu việc trễ."},
            "alternatives": ["Chờ kỳ sau đo lại trước khi hành động."],
            "timeline": "Trong 14 ngày; kiểm tra 24h/7d sau khi giao việc.",
            "owner": "MGR",
        }  # fmt: skip
        pillar = "O"  # KPI/OKR execution health maps to the people/execution pillar
        severity = "CRITICAL" if band_in.upper() == "CRITICAL" else "WARNING"
        draft = InsightDraft(pillar, "recommendation", severity, observation, structured, evidence)
        return await self._persist(draft, "MEDIUM")

    async def generate_for_okr(self, payload: dict[str, Any]) -> Insight | None:
        """A KR at-risk transition (`execution.okr_at_risk`) → one 9-part insight whose root cause
        is a **blocker analysis** (the KR's own at-risk reasons + the owner's overdue workload) and
        an **L2** recommendation: an intervention task tied to the KR (MGR approves; executed at L3
        via the Action Registry, then followed up/verified — R-DEC-143, UC-04). Grounded on the KR
        progress number itself. Reuses existing signals only (no new engine).
        """
        kr_id = str(payload.get("key_result_id", ""))
        obj_id = str(payload.get("objective_id", ""))
        period = str(payload.get("period_key", ""))
        raw = payload.get("progress_pct")
        if raw is None:
            return None
        try:
            progress = float(raw)
        except (TypeError, ValueError):
            return None
        expected = payload.get("expected_progress_pct")
        reasons = [str(r) for r in (payload.get("reasons") or [])]
        overdue = await self._owner_overdue(payload)
        evidence = [
            SourceRefOut(
                type="metric_value",
                id=f"KR:{kr_id}",
                label="Tiến độ KR",
                period_key=period,
                value=progress,
                lineage_url=f"/goals/okrs/{obj_id}",
            ).model_dump()
        ]
        blockers = ", ".join(reasons) if reasons else "chưa rõ lý do cụ thể"
        root = f"Phân tích blocker: {blockers}" + (
            f"; {overdue} việc quá hạn của người phụ trách (workload)." if overdue else "."
        )
        impact = f"KR đạt {progress:g}% (kỳ vọng {expected}%) — rủi ro lệch mục tiêu kỳ {period}."
        conf_reason = "Tiến độ KR tươi + tín hiệu blocker/việc trễ."
        structured = {
            "impact": impact,
            "root_cause": root,
            "risk": "Giữ nguyên đà này KR sẽ không về đích kỳ.",
            "expected_outcome": {"metric_id": f"KR:{kr_id}", "target": "về kỳ vọng", "by": "+14d"},
            # L2: a proposed intervention task tied to the KR — MGR confirms via an ActionCard.
            "action": [{
                "text": "Giao việc can thiệp gỡ blocker cho KR (chờ MGR duyệt)",
                "tool": "TOOL-create_task", "autonomy_level": "L2",
                "input": {"key_result_id": kr_id, "objective_id": obj_id, "period_key": period},
            }],
            "evidence": evidence,
            "confidence": {"band": "MEDIUM", "reason": conf_reason},
            "alternatives": ["Điều chỉnh phạm vi KR thay vì thêm việc."],
            "timeline": "Trong 14 ngày; theo dõi + verify 24h/7d sau khi giao việc (UC-04).",
            "owner": "MGR",
        }  # fmt: skip
        observation = (
            f"KR đang ở mức rủi ro: đạt {progress:g}% so với kỳ vọng {expected}% kỳ {period}."
        )
        draft = InsightDraft("O", "recommendation", "WARNING", observation, structured, evidence)
        return await self._persist(draft, "MEDIUM")

    async def _owner_overdue(self, payload: dict[str, Any]) -> int:
        """Count the KPI owner's overdue tasks (root-cause signal) via the `execution` public
        service — scoped to a system MGR principal for the owner's department (no cross-schema
        query, DEC-125). Returns 0 when the owner is unknown or the read fails."""
        from app.core.deps import Principal
        from app.core.pagination import PageParams
        from app.modules.execution.services.task_service import TaskService

        owner = payload.get("owner_id")
        dept = payload.get("department_id")
        if not owner:
            return 0
        actor = Principal(
            user_id=uuid.UUID(str(owner)), role="MGR",
            permissions=frozenset({"execution:read"}),
            department_id=uuid.UUID(str(dept)) if dept else None,
            employee_id=uuid.UUID(str(owner)),
        )  # fmt: skip
        try:
            _items, total = await TaskService(self.db).list_tasks(
                actor, PageParams(limit=5, offset=0, sort_by="due_date", order="asc"),
                filters={}, overdue=True,
            )  # fmt: skip
        except Exception:  # a read failure must not drop the insight (root cause falls back)
            return 0
        return int(total)

    async def _narrate(self, pillar: str, worst: Any, evidence: list[dict[str, Any]]) -> str:
        default = f"Trụ {pillar}: {worst.metric_code} đang ở mức {worst.status}."
        if self.gateway is None:
            return default
        req = ChatRequest(
            task="insight", caller_module="ai", classification="INTERNAL",
            messages=(
                GwMessage("system", "Viết MỘT câu tiếng Việt mô tả điều bất thường, "
                          "chỉ dùng số trong DATA. Không thêm số mới."),
                GwMessage("user", wrap_data("metrics", str(evidence))),
            ),
            temperature=0.2,
        )  # fmt: skip
        resp = await self.gateway.chat(req)
        return resp.content.strip() or default

    def _confidence(self, metrics: list[Any]) -> tuple[str, str]:
        fresh = all(getattr(m, "freshness", "fresh") == "fresh" for m in metrics)
        if fresh and len(metrics) >= 2:
            return "HIGH", "Nhiều chỉ số tươi cùng hướng."
        if fresh:
            return "MEDIUM", "Một chỉ số tươi, cỡ mẫu nhỏ."
        return "LOW", "Dữ liệu có chỉ số cũ (stale)."

    async def _persist(self, draft: InsightDraft, band: str) -> Insight | None:
        # grounding gate: an insight must keep ≥ 1 evidence source (GAP D-15)
        if not draft.evidence:
            return None
        insight = Insight(
            kind=draft.kind, pillar=draft.pillar, title=draft.observation[:200],
            body=draft.observation, severity=draft.severity, confidence=band,
            sources=draft.evidence, structured=draft.structured,
            audience_roles=PILLAR_AUDIENCE.get(draft.pillar, ["CEO"]),
            status="active", source="AI", expires_at=datetime.now(UTC) + INSIGHT_TTL,
        )  # fmt: skip
        self.db.add(insight)
        await self.db.flush()
        return insight

    # ---------- reads (EP-114) ----------
    async def list_for(
        self, user: Principal, *, pillar: str | None = None, kind: str | None = None,
        severity: str | None = None,
    ) -> list[InsightOut]:  # fmt: skip
        pillars = visible_pillars(user)
        rows = await InsightRepository(self.db).active_for_role(
            user.role, pillar=pillar, kind=kind,
            severity=severity.upper() if severity is not None else None,
        )  # fmt: skip
        out: list[InsightOut] = []
        for ins in rows:
            # hide an insight whose pillar the viewer cannot see (scope, 02 §6), or whose
            # evidence holds a metric outside the viewer's field scope — e.g. a DIR {O} sees
            # pillar F only for the public METRIC-FIN-01 headline (02 §6.1), not runway / budget
            if ins.pillar is not None and ins.pillar not in pillars:
                continue
            if not all(
                metric_visible(user, str(ev.get("id")), ins.pillar)
                for ev in ins.sources or []
                if ev.get("type") == "metric_value"
            ):
                continue
            out.append(self._to_out(ins))
        return out

    async def dismiss(self, user: Principal, insight_id: uuid.UUID) -> InsightOut:
        from app.core.errors import NotFoundError

        ins = await InsightRepository(self.db).for_role(insight_id, user.role)
        if ins is None:
            raise NotFoundError("insight not found")
        ins.status = "dismissed"
        await self.db.flush()
        return self._to_out(ins)

    def _to_out(self, ins: Insight) -> InsightOut:
        structured = ins.structured or {}
        recs = [
            RecommendationOut(text=a.get("text", ""), action=a)
            for a in structured.get("action", [])
            if isinstance(a, dict)
        ]
        sev = ins.severity.lower() if ins.severity else "info"
        eo = structured.get("expected_outcome")
        return InsightOut(
            id=ins.id,
            kind=ins.kind,
            pillar=ins.pillar,
            severity=sev,
            observation=ins.body,
            evidence=[SourceRefOut.model_validate(s) for s in (ins.sources or [])],
            impact=structured.get("impact") or structured.get("risk"),
            root_cause=structured.get("root_cause"),
            risk=structured.get("risk"),
            recommendations=recs,
            expected_outcome=eo if isinstance(eo, dict) else None,
            confidence=ConfidenceOut(
                band=ins.confidence.lower(),
                reason=(structured.get("confidence") or {}).get("reason", ""),
            ),
            structured=structured,
            created_at=ins.created_at,
            expires_at=ins.expires_at,
        )
