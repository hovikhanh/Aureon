"""R-DEC-76 — ADM `idp:read` + `idp:write` scope `s` (only doc type #4 HR_ROSTER).

Target ACTs still check `hr:*` (R-DEC-61); level-4 columns are dropped by ACT-create_employee
(test_action_registry_v2). Pulled forward from M1.6 (TC-M16-14/16 cover the full wizard).
"""

import pytest

from app.core.deps import Principal
from app.core.errors import ScopeDeniedError
from app.modules.auth.permission_matrix import ROLE_PERMISSIONS, ROLE_SCOPES
from app.modules.idp.services.scope import ensure_doc_type_scope
from tests.conftest import ApiClient

pytestmark = pytest.mark.integration
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def test_matrix_grants_adm_idp_read_write_scope_s() -> None:
    assert {"idp:read", "idp:write", "idp:admin"} <= set(ROLE_PERMISSIONS["ADM"])
    assert ROLE_SCOPES["ADM"]["idp:read"] == ROLE_SCOPES["ADM"]["idp:write"] == "s"
    assert "idp:approve" not in ROLE_PERMISSIONS["ADM"]


def test_scope_guard() -> None:
    import uuid

    adm = Principal(user_id=uuid.uuid4(), role="ADM",
                    permissions=frozenset(ROLE_PERMISSIONS["ADM"]))  # fmt: skip
    ensure_doc_type_scope(adm, "HR_ROSTER")
    for code in ("INVOICE", "PLAN_KPI_OKR", None):
        with pytest.raises(ScopeDeniedError):
            ensure_doc_type_scope(adm, code)
    ceo = Principal(user_id=uuid.uuid4(), role="CEO",
                    permissions=frozenset(ROLE_PERMISSIONS["CEO"]))  # fmt: skip
    ensure_doc_type_scope(ceo, "INVOICE")


async def test_adm_lists_document_types(api: ApiClient) -> None:
    r = await api.call("GET", "/data-capture/document-types", "ADMIN",
                       params={"include_inactive": "true"})  # fmt: skip
    assert r.status_code == 200, r.text
    assert "HR_ROSTER" in {t["code"] for t in r.json()["data"]}


@pytest.mark.parametrize("doc_type", ["INVOICE", "PLAN_KPI_OKR", None])
async def test_adm_upload_non_roster_forbidden_scope(api: ApiClient, doc_type) -> None:
    data = {"document_type": doc_type} if doc_type else {}
    h = api.headers("ADMIN", idem=True)
    r = await api.http.post("/api/v1/idp/documents", headers=h, data=data,
                            files=[("files", ("a.xlsx", b"x", XLSX))])  # fmt: skip
    assert r.status_code == 403, r.text
    assert r.json()["error"]["code"] == "FORBIDDEN_SCOPE"


async def test_adm_import_scope(api: ApiClient) -> None:
    h = api.headers("ADMIN", idem=True)
    files = [("file", ("ds.xlsx", b"x", XLSX))]
    bad = await api.http.post("/api/v1/data-capture/imports", headers=h,
                              data={"document_type": "PERIOD_REPORT"}, files=files)  # fmt: skip
    assert bad.status_code == 403 and bad.json()["error"]["code"] == "FORBIDDEN_SCOPE"
    h2 = api.headers("ADMIN", idem=True)
    ok = await api.http.post("/api/v1/data-capture/imports", headers=h2,
                             data={"document_type": "HR_ROSTER"}, files=files)  # fmt: skip
    # scope passes (not 403); the 1-byte body is not an OOXML zip → 415 (TC-M15-05)
    assert ok.status_code == 415, ok.text
    form = await api.call("GET", "/data-capture/forms/INVOICE", "ADMIN")
    assert form.status_code == 403
