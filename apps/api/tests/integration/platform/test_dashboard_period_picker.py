"""T-510 — the dashboard period picker's 4 choices resolve on every pillar endpoint.

The FE picker sends `period` = `2026-10` (this month at DEMO_REFERENCE_DATE), `2026-09` (last
month, default — DEC-237), `2026-Q3`, `2026-Q4` to EP-60/70/80/90/100 + EP-49 (O = hr + execution).
Each must answer 200 with `period.key` echoed and a pillar status; month/quarter shapes differ.
"""

import pytest

pytestmark = pytest.mark.integration

DOMAINS = ("finance", "sales", "hr", "execution", "product", "risk")
PERIODS = {"2026-10": "month", "2026-09": "month", "2026-Q3": "quarter", "2026-Q4": "quarter"}


@pytest.mark.parametrize("period", list(PERIODS))
async def test_picker_periods_resolve_on_all_pillars(api, period: str) -> None:
    for domain in DOMAINS:
        r = await api.call("GET", f"/{domain}/dashboard", role="CEO", params={"period": period})
        assert r.status_code == 200, (domain, r.text)
        data = r.json()["data"]
        assert data["period"]["key"] == period
        assert data["period"]["type"] == PERIODS[period]
        assert data["status"] in {"ok", "warning", "critical", "no_data"}
        assert data["metrics"], domain


async def test_finance_october_differs_from_september(api) -> None:
    """Selecting 'Tháng này' really changes the numbers (not the same cached payload)."""
    sep = await api.call("GET", "/finance/dashboard", role="CEO", params={"period": "2026-09"})
    oct_ = await api.call("GET", "/finance/dashboard", role="CEO", params={"period": "2026-10"})
    s = sep.json()["data"]["summary"]
    o = oct_.json()["data"]["summary"]
    assert s["total_revenue"] != o["total_revenue"]
    assert sep.headers["vary"].lower().count("authorization") == 1


@pytest.mark.parametrize("domain", DOMAINS)
@pytest.mark.parametrize("bad", ["2026-13", "2026-Q9"])
async def test_bad_period_is_400(api, domain: str, bad: str) -> None:
    r = await api.call("GET", f"/{domain}/dashboard", role="CEO", params={"period": bad})
    assert r.status_code == 400
    details = r.json()["error"]["details"]
    assert "period" in (details.get("param"), details.get("field"))
