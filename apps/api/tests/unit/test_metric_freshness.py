"""TC-M21-03/10 (unit) — MetricValueOut.group + freshness theo SLA_FRESHNESS_* (R-DEC-86)."""

from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.core.config import get_config
from app.modules.dashboard.schemas import MetricValueOut
from app.modules.platform.services.metric_query import value_dto


def _metric(code: str, source_module: str, pillar: str | None = "F") -> SimpleNamespace:
    return SimpleNamespace(code=code, pillar=pillar, unit="PERCENT", source_module=source_module)


def _value(computed_at: datetime) -> SimpleNamespace:
    return SimpleNamespace(
        value=82,
        threshold_status="GREEN",
        period_key="2026-10",
        computed_at=computed_at,
        data_quality_score=99,
    )


def test_fresh_within_window_and_group_is_set() -> None:
    now = datetime.now(UTC)
    dto = value_dto(_metric("METRIC-FIN-01", "finance"), _value(now - timedelta(hours=2)), now)
    assert dto.group == "FIN"
    assert dto.is_stale is False
    assert dto.freshness == "fresh"
    assert dto.max_age_hours == get_config().freshness_hours("finance")


def test_stale_when_older_than_domain_window() -> None:
    now = datetime.now(UTC)
    # finance window = 24h → 30h old là stale
    dto = value_dto(_metric("METRIC-FIN-01", "finance"), _value(now - timedelta(hours=30)), now)
    assert dto.is_stale is True
    assert dto.freshness == "stale"


def test_hr_window_is_longer_than_finance() -> None:
    now = datetime.now(UTC)
    old = _value(now - timedelta(hours=48))
    # 48h: hr (72h) còn fresh, finance (24h) đã stale → ngưỡng theo domain, không hard-code
    hr = value_dto(_metric("METRIC-HR-01", "hr", "O"), old, now)
    fin = value_dto(_metric("METRIC-FIN-01", "finance"), old, now)
    assert hr.is_stale is False and fin.is_stale is True


def test_dto_maps_cleanly_onto_schema() -> None:
    now = datetime.now(UTC)
    dto = value_dto(_metric("METRIC-STR-02", "execution", "S"), _value(now), now)
    out = MetricValueOut(**asdict(dto))
    assert out.group == "STR"
    assert out.max_age_hours == dto.max_age_hours
    assert out.is_stale == dto.is_stale
