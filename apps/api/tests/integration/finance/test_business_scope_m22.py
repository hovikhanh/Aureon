"""TC-M22-01 (M2.2, R-DEC-89) — khối-scope của Finance Lite (pillar F) vs Sales Lite (pillar C).

Đọc pillar-scoped (`require_pillar_permission`, EP `:read`): DIR-F (CFO) đọc finance nhưng bị
chặn sales; DIR-C (VP_SALES) ngược lại. Aggregate dashboard (`require_permission :query`) mở cho
mọi DIR theo thiết kế (10 §7.2.7). Thuộc nhóm bảo mật (≥90%)."""

import pytest

from tests.conftest import ApiClient

pytestmark = pytest.mark.integration

FIN_READ = "/finance/revenues"  # pillar-scoped (finance:read)
SAL_READ = "/sales/deals"  # pillar-scoped (sales:read)
FIN_QUERY = "/finance/dashboard"  # aggregate (finance:query — open to all DIR)
SAL_QUERY = "/sales/pipeline"  # aggregate (sales:query — open to all DIR)


async def _code(resp: object) -> str:
    return resp.json()["error"]["code"]  # type: ignore[attr-defined]


async def test_cfo_pillar_read_finance_blocks_sales(api: ApiClient) -> None:
    assert (await api.call("GET", FIN_READ, role="CFO")).status_code == 200
    blocked = await api.call("GET", SAL_READ, role="CFO")
    assert blocked.status_code == 403
    assert await _code(blocked) in ("FORBIDDEN_SCOPE", "FORBIDDEN_ROLE")


async def test_vp_sales_pillar_read_sales_blocks_finance(api: ApiClient) -> None:
    assert (await api.call("GET", SAL_READ, role="VP_SALES")).status_code == 200
    blocked = await api.call("GET", FIN_READ, role="VP_SALES")
    assert blocked.status_code == 403
    assert await _code(blocked) in ("FORBIDDEN_SCOPE", "FORBIDDEN_ROLE")


async def test_aggregate_dashboards_open_to_all_dir(api: ApiClient) -> None:
    # `:query` is pillar-agnostic by design — CFO may read the sales pipeline aggregate and
    # VP_SALES the finance dashboard aggregate; CEO reads everything.
    assert (await api.call("GET", SAL_QUERY, role="CFO")).status_code == 200
    assert (await api.call("GET", FIN_QUERY, role="VP_SALES")).status_code == 200
    for url in (FIN_QUERY, SAL_QUERY, FIN_READ, SAL_READ):
        assert (await api.call("GET", url, role="CEO")).status_code == 200, url
