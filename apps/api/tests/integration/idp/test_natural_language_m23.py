"""M2.3 (T-717) — EP-DC-38 POST /data-capture/natural-language contract guards.

TC-M23-01: context=meeting → 422 BUSINESS_RULE_VIOLATION (reason=meeting_audio_blocked,
R-DEC-22); exactly-one-of text/audio_ref (R-DEC-96); idp:write required.
"""

import pytest

from tests.conftest import ApiClient

pytestmark = pytest.mark.integration


async def test_meeting_context_blocked(api: ApiClient, db_session, idp_store) -> None:
    r = await api.call(
        "POST", "/data-capture/natural-language", "CEO",
        json={"text": "Giao anh Minh soạn báo cáo", "channel": "C2", "context": "meeting"},
    )  # fmt: skip
    assert r.status_code == 422
    err = r.json()["error"]
    assert err["code"] == "BUSINESS_RULE_VIOLATION"
    assert err["details"]["reason"] == "meeting_audio_blocked"


async def test_requires_exactly_one_of_text_or_audio(api: ApiClient, db_session, idp_store) -> None:
    both = await api.call(
        "POST", "/data-capture/natural-language", "CEO",
        json={"text": "x", "audio_ref": "a", "channel": "C2"},
    )  # fmt: skip
    assert both.status_code == 422
    neither = await api.call(
        "POST", "/data-capture/natural-language", "CEO", json={"channel": "C2"}
    )
    assert neither.status_code == 422


async def test_channel_must_be_c2(api: ApiClient, db_session, idp_store) -> None:
    r = await api.call(
        "POST", "/data-capture/natural-language", "CEO",
        json={"text": "ghi chú", "channel": "C3"},
    )  # fmt: skip
    assert r.status_code == 422
