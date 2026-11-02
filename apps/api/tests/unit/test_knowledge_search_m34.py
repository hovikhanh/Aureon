"""TC-M34-02 — Knowledge/RAG pure helpers (M3.4, R-DEC-141). No DB, no provider.

Covers `hash_embedding` (deterministic, unit-norm, distinct per text, gated dim), the gateway
`embed` gate (disabled when `embedding_model` empty → AI_NO_DATA_AVAILABLE; fixture otherwise),
and the snippet extractor used by both EP-24 and `TOOL-search_documents`.
"""

import math

import pytest

from app.core.errors import AppError
from app.core.model_gateway import ModelGateway, NullSink, hash_embedding
from app.modules.idp.services.knowledge_search import SNIPPET_LEN, _snippet


def test_hash_embedding_is_deterministic_unit_norm() -> None:
    a = hash_embedding("doanh thu quý 3")
    b = hash_embedding("doanh thu quý 3")
    assert a == b
    assert len(a) == 1024
    assert math.isclose(math.sqrt(sum(x * x for x in a)), 1.0, rel_tol=1e-9)


def test_hash_embedding_distinct_per_text() -> None:
    assert hash_embedding("doanh thu") != hash_embedding("chi phí")


@pytest.mark.asyncio
async def test_embed_gated_off_when_model_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    gw = ModelGateway(NullSink())
    monkeypatch.setattr(gw.cfg, "embedding_model", "")
    with pytest.raises(AppError) as ei:
        await gw.embed(["x"], caller_module="idp")
    assert ei.value.code == "AI_DISABLED"


@pytest.mark.asyncio
async def test_embed_fixture_returns_vectors() -> None:
    gw = ModelGateway(NullSink())
    out = await gw.embed(["a", "b"], caller_module="idp")
    assert len(out) == 2 and len(out[0]) == 1024


def test_snippet_centers_on_match() -> None:
    body = "trước " * 40 + "TỪ_KHÓA " + "sau " * 40
    snip = _snippet(body, "từ_khóa")
    assert "TỪ_KHÓA" in snip
    assert len(snip) <= SNIPPET_LEN + 2  # plus ellipses


def test_snippet_handles_no_match_and_empty() -> None:
    assert _snippet(None, "x") == ""
    long = "a" * (SNIPPET_LEN * 2)
    out = _snippet(long, "zzz")
    assert out.endswith("…") and len(out) == SNIPPET_LEN + 1
