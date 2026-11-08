"""F-H2 — an embedding outage or an empty vector index never fails document search."""

import uuid
from typing import Any

import httpx
import pytest
import respx
from sqlalchemy import select

from app.core.config import get_config
from app.core.deps import Principal
from app.core.errors import ai_error
from app.core.model_gateway import ModelGateway, NullSink
from app.core.model_gateway.gateway import EMBED_DIM
from app.modules.auth.permission_matrix import ROLE_PERMISSIONS
from app.modules.idp.models import DocumentPage, SourceDocument
from app.modules.idp.services.knowledge_index import KnowledgeIndexService
from app.modules.idp.services.knowledge_search import KnowledgeSearchService

pytestmark = pytest.mark.integration


def _ceo() -> Principal:
    return Principal(user_id=uuid.uuid4(), role="CEO",
                     permissions=frozenset(ROLE_PERMISSIONS["CEO"]))  # fmt: skip


async def _doc(db, text: str, level: int = 3) -> SourceDocument:
    doc = SourceDocument(
        channel="C3", kind="FILE", original_filename="d.pdf", mime_type="application/pdf",
        scan_status="CLEAN", pillars=[], status="NEEDS_REVIEW", sensitivity_level=level,
        source="IDP", data_classification="CONFIDENTIAL", submitted_at=_now(),
        submitted_by=uuid.uuid4(),
    )  # fmt: skip
    db.add(doc)
    await db.flush()
    db.add(DocumentPage(source_document_id=doc.id, page_number=1, text_layer_exists=True,
                        ocr_used=False, text_content=text))  # fmt: skip
    await db.flush()
    return doc


def _now() -> Any:
    from datetime import UTC, datetime

    return datetime.now(UTC)


class _Down:
    calls = 0

    async def embed(self, texts: list[str], **kw: Any) -> list[list[float]]:
        _Down.calls += 1
        raise ai_error("AI_PROVIDER_ERROR", "embedding down")


async def test_embedding_failure_falls_back_to_keyword(db_session) -> None:
    await _doc(db_session, "Hợp đồng bảo trì máy in với Zqxvendor")
    svc = KnowledgeSearchService(db_session, _Down())
    hits, total = await svc.search(_ceo(), "máy in với Zqxvendor")
    assert total == 1 and hits[0].page_number == 1
    assert "máy in với Zqxvendor" in hits[0].snippet
    assert svc.last_mode == "keyword"


async def test_no_vectors_yet_falls_back_to_keyword(db_session, monkeypatch) -> None:
    await _doc(db_session, "Biên bản họp Zqxmeeting tháng 9")

    class _Ok:
        async def embed(self, texts: list[str], **kw: Any) -> list[list[float]]:
            return [[0.1] * EMBED_DIM]

    async def _empty(*a: Any, **kw: Any) -> tuple[list[Any], int]:
        return [], 0

    svc = KnowledgeSearchService(db_session, _Ok())
    monkeypatch.setattr(svc.repo, "semantic", _empty)  # the slot may hold indexed live documents
    hits, _ = await svc.search(_ceo(), "Zqxmeeting")
    assert len(hits) == 1 and svc.last_mode == "keyword"


async def test_sentence_query_matches_on_its_words(db_session) -> None:
    doc = await _doc(db_session, "Hợp đồng bảo trì máy in với Zqxvendor")
    svc = KnowledgeSearchService(db_session, _Down())
    hits, _ = await svc.search(_ceo(), "tìm hợp đồng của Zqxvendor giúp tôi", limit=20)
    assert doc.id in {h.document_id for h in hits}


async def test_level_4_document_is_excluded_for_the_ai_tool(db_session) -> None:
    await _doc(db_session, "Danh sách lương Zqxsalary", level=4)
    svc = KnowledgeSearchService(db_session, _Down())
    assert (await svc.search(_ceo(), "Zqxsalary"))[1] == 1  # the HTTP scope is unchanged
    assert (await svc.search(_ceo(), "Zqxsalary", max_sensitivity=3))[1] == 0


async def test_index_embeds_pages_and_skips_level_4(db_session, monkeypatch) -> None:
    keep = await _doc(db_session, "Báo cáo tài chính quý 3")
    skip = await _doc(db_session, "Bảng lương", level=4)
    seen: list[str] = []

    class _Gw:
        async def embed(self, texts: list[str], **kw: Any) -> list[list[float]]:
            seen.extend(texts)
            return [[0.5] * EMBED_DIM for _ in texts]

    assert await KnowledgeIndexService(db_session, _Gw()).index_document(keep.id) == 1
    assert await KnowledgeIndexService(db_session, _Gw()).index_document(skip.id) == 0
    page = (await db_session.execute(select(DocumentPage).where(
        DocumentPage.source_document_id == keep.id))).scalar_one()  # fmt: skip
    assert page.embedding is not None and page.embedding_model == get_config().embedding_model
    assert seen == ["Báo cáo tài chính quý 3"]


@respx.mock
async def test_live_embed_uses_local_ollama_only_and_logs(monkeypatch) -> None:
    cfg = get_config().model_copy(update={
        "model_gateway_mode": "live", "ollama_base_url": "http://ollama.test:11434",
        "embedding_model": "bge-m3", "model_provider_primary": "omniroute",
    })  # fmt: skip
    cloud = respx.post(url__regex=r"https://.*").mock(return_value=httpx.Response(500))
    local = respx.post("http://ollama.test:11434/v1/embeddings").mock(
        return_value=httpx.Response(200, json={
            "data": [{"index": 0, "embedding": [0.0] * EMBED_DIM}],
            "usage": {"prompt_tokens": 7, "total_tokens": 7},
        })
    )  # fmt: skip
    sink = NullSink()
    out = await ModelGateway(sink, cfg=cfg).embed(["xin chào"], caller_module="idp")
    assert len(out[0]) == EMBED_DIM
    assert local.called and not cloud.called
    assert sink.records[-1].provider == "ollama" and sink.records[-1].model == "bge-m3"
    assert sink.records[-1].task_kind == "embed" and sink.records[-1].tokens_in == 7


@respx.mock
async def test_live_embed_failure_is_logged_and_raised_as_ai_error() -> None:
    cfg = get_config().model_copy(update={
        "model_gateway_mode": "live", "ollama_base_url": "http://ollama.test:11434",
    })  # fmt: skip
    respx.post("http://ollama.test:11434/v1/embeddings").mock(return_value=httpx.Response(500))
    sink = NullSink()
    with pytest.raises(Exception) as exc:
        await ModelGateway(sink, cfg=cfg).embed(["x"], caller_module="idp")
    assert exc.value.code == "AI_PROVIDER_ERROR"
    assert sink.records[-1].status == "error"


async def test_secret_is_never_embedded() -> None:
    from app.core.model_gateway.errors import SecretDataBlockedError

    with pytest.raises(SecretDataBlockedError):
        await ModelGateway(NullSink()).embed(["x"], caller_module="idp", classification="SECRET")


async def test_semantic_ranks_real_vectors(db_session) -> None:
    near = await _doc(db_session, "tài liệu gần")
    far = await _doc(db_session, "tài liệu xa")

    class _Gw:
        async def embed(self, texts: list[str], **kw: Any) -> list[list[float]]:
            return [[1.0] + [0.0] * (EMBED_DIM - 1)]

    for doc, head in ((near, [1.0, 0.0]), (far, [0.0, 1.0])):
        page = (await db_session.execute(select(DocumentPage).where(
            DocumentPage.source_document_id == doc.id))).scalar_one()  # fmt: skip
        page.embedding = head + [0.0] * (EMBED_DIM - 2)
    await db_session.flush()
    svc = KnowledgeSearchService(db_session, _Gw())
    hits, total = await svc.search(_ceo(), "câu hỏi không có trong tài liệu")
    assert svc.last_mode == "semantic" and total >= 2
    assert hits[0].document_id == near.id
