"""IdpQueryService data scoping (02 §6): a non-admin, department-scoped reader sees documents
they submitted or in their department, not others'; extraction returns None before a job runs."""

from __future__ import annotations

import uuid

import pytest

from app.core.deps import Principal
from app.modules.auth.permission_matrix import ROLE_PERMISSIONS
from app.modules.idp.services.query_service import IdpQueryService
from app.modules.idp.services.upload_service import UploadFile, UploadService
from tests.integration.idp import sample_docs as s

pytestmark = pytest.mark.integration


def _emp(dept: uuid.UUID, uid: uuid.UUID | None = None) -> Principal:
    return Principal(
        user_id=uid or uuid.uuid4(),
        role="EMP",
        permissions=frozenset(ROLE_PERMISSIONS["EMP"]),
        department_id=dept,
    )


def _file() -> UploadFile:
    return UploadFile("a.pdf", "application/pdf", iter([s.invoice_pdf()]))


async def test_reader_sees_own_and_same_department_only(db_session, idp_store) -> None:
    dept_a, dept_b = uuid.uuid4(), uuid.uuid4()
    submitter = _emp(dept_a)
    r = await UploadService(db_session).upload(submitter, [_file()])
    doc_id = r.document_ids[0]
    q = IdpQueryService(db_session)

    # same department reader → visible
    assert await q.get_document(_emp(dept_a), doc_id) is not None
    # other department reader → hidden
    assert await q.get_document(_emp(dept_b), doc_id) is None
    # the QUEUED job exists but has no field results until the pipeline runs
    ex = await q.get_extraction(_emp(dept_a), doc_id)
    assert ex is not None and ex.status == "QUEUED" and ex.fields == []
    # other department reader cannot read the extraction either
    assert await q.get_extraction(_emp(dept_b), doc_id) is None


async def test_pipeline_gateway_factory_and_public_service(db_session) -> None:
    import importlib

    importlib.import_module("app.modules.ai")  # composition root registers the call-log sink
    from app.modules.idp.services import IdpService
    from app.modules.idp.services.gateway import pipeline_gateway

    gw = pipeline_gateway(db_session)
    assert hasattr(gw, "chat")
    assert IdpService(db_session).db is db_session


async def test_admin_sees_only_structure_doc_types(db_session, idp_store) -> None:
    """R-DEC-76: ADM `idp:read` scope `s` — a non-#4 document is invisible (404 upstream)."""
    submitter = _emp(uuid.uuid4())
    r = await UploadService(db_session).upload(submitter, [_file()])
    admin = Principal(
        user_id=uuid.uuid4(),
        role="ADM",
        permissions=frozenset(ROLE_PERMISSIONS["ADM"]),
        department_id=None,
    )
    assert await IdpQueryService(db_session).get_document(admin, r.document_ids[0]) is None
    rev = frozenset(ROLE_PERMISSIONS["REV"])
    no_dept = Principal(user_id=uuid.uuid4(), role="REV", permissions=rev, department_id=None)
    assert await IdpQueryService(db_session).get_document(no_dept, r.document_ids[0]) is not None


async def test_ceo_with_a_department_sees_every_department(db_session, idp_store) -> None:
    """02 §2: ROLE-CEO scope = toàn doanh nghiệp, even when seeded into the BGĐ department."""
    r = await UploadService(db_session).upload(_emp(uuid.uuid4()), [_file()])
    ceo = Principal(
        user_id=uuid.uuid4(),
        role="CEO",
        permissions=frozenset(ROLE_PERMISSIONS["CEO"]),
        department_id=uuid.uuid4(),
    )
    q = IdpQueryService(db_session)
    assert await q.get_document(ceo, r.document_ids[0]) is not None
    assert await q.get_document(_emp(uuid.uuid4()), r.document_ids[0]) is None
