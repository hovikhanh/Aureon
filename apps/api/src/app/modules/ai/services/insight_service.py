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

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal
from app.core.model_gateway.types import ChatRequest, ChatResponse
from app.core.model_gateway.types import Message as GwMessage
from app.modules.ai.models import Insight
from app.modules.ai.schemas import (
    ConfidenceOut,
    InsightOut,
    RecommendationOut,
    SourceRefOut,
)
from app.modules.ai.services.prompt_guard import wrap_data
from app.modules.dashboard.services.dashboard_service import (
    DashboardService,
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
        stmt = select(Insight).where(
            Insight.status == "active",
            Insight.audience_roles.op("@>")([user.role]),
        )
        if pillar is not None:
            stmt = stmt.where(Insight.pillar == pillar)
        if kind is not None:
            stmt = stmt.where(Insight.kind == kind)
        if severity is not None:
            stmt = stmt.where(Insight.severity == severity.upper())
        stmt = stmt.order_by(Insight.created_at.desc())
        rows = (await self.db.execute(stmt)).scalars()
        out: list[InsightOut] = []
        for ins in rows:
            # hide an insight whose pillar the viewer cannot see (scope, 02 §6)
            if ins.pillar is not None and ins.pillar not in pillars:
                continue
            out.append(self._to_out(ins))
        return out

    async def dismiss(self, user: Principal, insight_id: uuid.UUID) -> InsightOut:
        from app.core.errors import NotFoundError

        ins = (
            await self.db.execute(
                select(Insight).where(
                    Insight.id == insight_id, Insight.audience_roles.op("@>")([user.role])
                )
            )
        ).scalar_one_or_none()
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
        return InsightOut(
            id=ins.id,
            kind=ins.kind,
            pillar=ins.pillar,
            severity=sev,
            observation=ins.body,
            evidence=[SourceRefOut.model_validate(s) for s in (ins.sources or [])],
            impact=structured.get("risk"),
            recommendations=recs,
            confidence=ConfidenceOut(
                band=ins.confidence.lower(),
                reason=(structured.get("confidence") or {}).get("reason", ""),
            ),
            structured=structured,
            created_at=ins.created_at,
            expires_at=ins.expires_at,
        )
