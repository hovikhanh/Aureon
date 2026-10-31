"""TC-M21-07 — EP-RPT-04/05 executive-tiles preference (bảo mật: scope + validate + optimistic).

Mặc định FIN-01/FIN-03/STR-01/OPS-01 version 0 (R-DEC-87); PUT ≤4 mã hợp lệ + trong scope;
Idempotency-Key bắt buộc (thiếu → 400); >4/mã lạ/trùng → 422; ngoài scope → 422 out_of_scope;
version lệch → 409; replay cùng key → cùng kết quả; audit platform.preference_update.
"""

import uuid
from typing import Any

from tests.conftest import ApiClient

URL = "/reporting/preferences/executive-tiles"
DEFAULT = ["METRIC-FIN-01", "METRIC-FIN-03", "METRIC-STR-01", "METRIC-OPS-01"]
# preference là per-user → pin user_id để các PUT trong một test trỏ cùng người (optimistic lock)
CEO_ID = uuid.UUID("00000000-0000-0000-0000-0000000000ce")


async def _put(api: ApiClient, tiles: list[str], version: int, **hdr: str) -> Any:
    h = ApiClient.headers("CEO", idem=True, user_id=CEO_ID)
    h.update(hdr)
    return await api.http.put(f"/api/v1{URL}", json={"tiles": tiles, "version": version}, headers=h)


async def test_get_default_tiles(api: ApiClient) -> None:
    res = await api.call("GET", URL, "CEO")
    assert res.status_code == 200, res.text
    assert res.headers["cache-control"] == "no-store"
    d = res.json()["data"]
    assert d["tiles"] == DEFAULT and d["version"] == 0


async def test_put_requires_idempotency_key(api: ApiClient) -> None:
    h = ApiClient.headers("CEO")  # không idem
    res = await api.http.put(
        f"/api/v1{URL}", json={"tiles": ["METRIC-FIN-01"], "version": 0}, headers=h
    )
    assert res.status_code == 400


async def test_put_valid_then_version_conflict(api: ApiClient) -> None:
    ok = await _put(api, ["METRIC-FIN-01", "METRIC-CUS-01"], 0)
    assert ok.status_code == 200, ok.text
    assert ok.json()["data"]["version"] == 1
    # version cũ (0) → 409
    stale = await _put(api, ["METRIC-FIN-01"], 0)
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "CONFLICT_STATE"


async def test_put_too_many_unknown_duplicate(api: ApiClient) -> None:
    five = [*DEFAULT, "METRIC-CUS-01"]
    assert (await _put(api, five, 0)).status_code == 422
    assert (await _put(api, ["METRIC-FAKE-99"], 0)).status_code == 422
    dup = await _put(api, ["METRIC-FIN-01", "METRIC-FIN-01"], 0)
    assert dup.status_code == 422


async def test_put_out_of_scope_for_dir(api: ApiClient) -> None:
    # DIR scope F chọn ô trụ S → 422 BUSINESS_RULE_VIOLATION reason=out_of_scope
    h = ApiClient.headers("CFO", idem=True)  # DIR, scope_pillars=(F,)
    res = await api.http.put(
        f"/api/v1{URL}", json={"tiles": ["METRIC-RSK-01"], "version": 0}, headers=h
    )
    assert res.status_code == 422, res.text
    err = res.json()["error"]
    assert err["code"] == "BUSINESS_RULE_VIOLATION"
    assert err["details"]["reason"] == "out_of_scope"


async def test_put_update_existing_bumps_version(api: ApiClient) -> None:
    v1 = await _put(api, ["METRIC-FIN-01"], 0)
    assert v1.json()["data"]["version"] == 1
    v2 = await _put(api, ["METRIC-CUS-01", "METRIC-OPS-01"], 1)  # version khớp → cập nhật
    assert v2.status_code == 200, v2.text
    assert v2.json()["data"]["version"] == 2
    assert v2.json()["data"]["tiles"] == ["METRIC-CUS-01", "METRIC-OPS-01"]


async def test_put_fresh_insert_wrong_version(api: ApiClient) -> None:
    # chưa có row mà gửi version != 0 → 409 (expected 0)
    res = await _put(api, ["METRIC-FIN-01"], 3)
    assert res.status_code == 409
    assert res.json()["error"]["details"]["expected"] == "0"


async def test_put_idempotent_replay(api: ApiClient) -> None:
    key = str(uuid.uuid4())
    r1 = await _put(api, ["METRIC-FIN-01"], 0, **{"Idempotency-Key": key})
    assert r1.status_code == 200, r1.text
    r2 = await _put(api, ["METRIC-FIN-01"], 0, **{"Idempotency-Key": key})
    assert r2.status_code == 200
    assert r1.json()["data"] == r2.json()["data"]
