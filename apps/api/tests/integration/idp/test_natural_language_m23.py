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


async def test_text_submit_runs_pipeline_and_previews(db_session, idp_store, monkeypatch) -> None:
    """TC-M23-01: text → stored as text/plain C2 → Pipeline → NOT-committed preview."""
    import uuid as _uuid

    from app.core.deps import Principal
    from app.core.model_gateway import ChatResponse
    from app.modules.auth.permission_matrix import ROLE_PERMISSIONS
    from app.modules.idp.schemas.capture import NaturalLanguageIn
    from app.modules.idp.services import natural_language as nl
    from app.modules.idp.services.natural_language import NaturalLanguageService

    class _Gw:
        async def chat(self, req):  # classify + extract fall back to OTHER (no keywords)
            return ChatResponse(content="", provider="fake", model="m", data={})

        async def extract(self, req):
            return ChatResponse(content="", provider="fake", model="m", data={})

        async def transcribe(self, *, audio_ref, caller_module, user_id=None):
            return ChatResponse(content="ghi chú từ giọng nói", provider="fake", model="stt")

    monkeypatch.setattr(nl, "pipeline_gateway", lambda _db: _Gw())
    ceo = Principal(user_id=_uuid.uuid4(), role="CEO", role_id="CEO",
                    permissions=frozenset(ROLE_PERMISSIONS["CEO"]))  # fmt: skip
    out = await NaturalLanguageService(db_session).submit(
        ceo, NaturalLanguageIn(text="Giao việc soạn báo cáo", channel="C2")
    )
    assert out.status in {"NEEDS_REVIEW", "AUTO_APPROVED"}
    assert out.document.id is not None


async def test_audio_submit_transcribes_then_previews(db_session, idp_store, monkeypatch) -> None:
    """TC-M23-02: audio_ref → STT transcribe (fixture-only) → text → Pipeline preview."""
    import uuid as _uuid

    from app.core.deps import Principal
    from app.core.model_gateway import ChatResponse
    from app.modules.auth.permission_matrix import ROLE_PERMISSIONS
    from app.modules.idp.schemas.capture import NaturalLanguageIn
    from app.modules.idp.services import natural_language as nl
    from app.modules.idp.services.natural_language import NaturalLanguageService

    seen: dict[str, object] = {}

    class _Gw:
        async def chat(self, req):
            return ChatResponse(content="", provider="fake", model="m", data={})

        async def extract(self, req):
            return ChatResponse(content="", provider="fake", model="m", data={})

        async def transcribe(self, *, audio_ref, caller_module, user_id=None):
            seen["audio_ref"] = audio_ref
            return ChatResponse(content="nội dung thoại", provider="fake", model="stt")

    monkeypatch.setattr(nl, "pipeline_gateway", lambda _db: _Gw())
    ceo = Principal(user_id=_uuid.uuid4(), role="CEO", role_id="CEO",
                    permissions=frozenset(ROLE_PERMISSIONS["CEO"]))  # fmt: skip
    out = await NaturalLanguageService(db_session).submit(
        ceo, NaturalLanguageIn(audio_ref="voice-note/x.webm", channel="C2")
    )
    assert seen["audio_ref"] == "voice-note/x.webm"  # STT was invoked
    assert out.document.id is not None
