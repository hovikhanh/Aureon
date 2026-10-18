"""Tests for C5 Spreadsheet Import (EP-23 & EP-36) endpoints (T-205).

Implements TC-IDP-007:
- EP-23 Excel 47 rows -> mapping_suggestion
- EP-36 confirm -> 47 record groups with source_location.kind=cell (sheet/row/col)
- Row errors report row_index without blocking valid rows (IDP-E11)
- > 5,000 rows -> 422 VALIDATION_ERROR
- Non-uploader calling EP-36 -> 403 FORBIDDEN_SCOPE
- Re-confirming -> 409 CONFLICT_STATE
"""

import io
import zipfile
from collections.abc import Generator
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_config
from app.main import app
from app.modules.audit.models import AuditLog
from app.modules.auth.models import Role, User
from app.modules.auth.token import create_access_token
from app.modules.idp.enums import SourceLocationKind
from app.modules.idp.models import ExtractedField

CONTENT_TYPES_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
    '<Default Extension="rels" '
    'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
    '<Default Extension="xml" ContentType="application/xml"/>\n'
    '<Override PartName="/xl/workbook.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>\n'
    '<Override PartName="/xl/worksheets/sheet1.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>\n'
    '<Override PartName="/xl/sharedStrings.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>\n'
    '</Types>'
)

RELS_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
    '<Relationship Id="rId1" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
    'Target="xl/workbook.xml"/>\n'
    '</Relationships>'
)

WORKBOOK_RELS_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
    '<Relationship Id="rId1" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
    'Target="worksheets/sheet1.xml"/>\n'
    '<Relationship Id="rId2" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" '
    'Target="sharedStrings.xml"/>\n'
    '</Relationships>'
)

WORKBOOK_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">\n'
    '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets>\n'
    '</workbook>'
)


def make_test_xlsx_bytes(headers: list[str], rows: list[list[Any]]) -> bytes:
    """Build a minimal valid XLSX file with shared strings and sheetData."""
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w") as zf:
        zf.writestr("[Content_Types].xml", CONTENT_TYPES_XML)
        zf.writestr("_rels/.rels", RELS_XML)
        zf.writestr("xl/_rels/workbook.xml.rels", WORKBOOK_RELS_XML)
        zf.writestr("xl/workbook.xml", WORKBOOK_XML)

        all_strings: list[str] = []
        string_map: dict[str, int] = {}

        def get_sid(val: Any) -> int:
            s = str(val)
            if s not in string_map:
                string_map[s] = len(all_strings)
                all_strings.append(s)
            return string_map[s]

        sheet_rows_xml: list[str] = []
        # Header row
        header_cells: list[str] = []
        for c_idx, h in enumerate(headers):
            col_letter = chr(65 + c_idx)
            sid = get_sid(h)
            header_cells.append(f'<c r="{col_letter}1" t="s"><v>{sid}</v></c>')
        sheet_rows_xml.append(f'<row r="1">{"".join(header_cells)}</row>')

        # Data rows
        for r_idx, row in enumerate(rows, start=2):
            cells_xml: list[str] = []
            for c_idx, val in enumerate(row):
                col_letter = chr(65 + c_idx)
                sid = get_sid(val)
                cells_xml.append(f'<c r="{col_letter}{r_idx}" t="s"><v>{sid}</v></c>')
            sheet_rows_xml.append(f'<row r="{r_idx}">{"".join(cells_xml)}</row>')

        ns_str = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
        count = len(all_strings)
        sst_xml = [f'<sst xmlns="{ns_str}" count="{count}" uniqueCount="{count}">']
        for s in all_strings:
            sst_xml.append(f"<si><t>{s}</t></si>")
        sst_xml.append("</sst>")
        zf.writestr("xl/sharedStrings.xml", "".join(sst_xml))

        ws_xml = (
            f'<worksheet xmlns="{ns_str}">'
            f'<sheetData>{"".join(sheet_rows_xml)}</sheetData></worksheet>'
        )
        zf.writestr("xl/worksheets/sheet1.xml", ws_xml)

    return bio.getvalue()


@pytest.fixture
def app_client(db_session: Session) -> Generator[TestClient, None, None]:
    from app.db.session import get_db

    app.dependency_overrides[get_db] = lambda: db_session
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def seed_test_users(db_session: Session) -> dict[str, tuple[User, str]]:
    cfg = get_config()
    roles = ["ROLE-01", "ROLE-02", "ROLE-05"]
    result: dict[str, tuple[User, str]] = {}
    for role_code in roles:
        email = f"{role_code.lower()}@abc.demo"
        user = db_session.execute(
            select(User).where(User.email == email, User.deleted_at.is_(None))
        ).scalar_one_or_none()
        if not user:
            stmt = select(Role).where(Role.code == role_code)
            role = db_session.execute(stmt).scalar_one_or_none()
            if not role:
                role = Role(
                    code=role_code,
                    name_i18n_key=f"shell.roles.{role_code}",
                    pillar_scope=["FIN"],
                    pillar_agg_scope=[],
                    review_pillars=["FIN"],
                    home_route="/dashboard",
                )
                db_session.add(role)
                db_session.flush()
            user = User(
                email=email,
                password_hash="$fake_hash",
                full_name=f"User {role_code}",
                salutation="anh",
                role_id=role.id,
                is_demo_account=True,
            )
            db_session.add(user)
            db_session.flush()

        token, _ = create_access_token(user, cfg)
        result[role_code] = (user, token)

    return result


DOC_02_HEADERS = [
    "STT",
    "Số HĐ",
    "Ngày",
    "Khách hàng",
    "MST khách",
    "Subtotal (VND)",
    "VAT %",
    "Đã thu (VND)",
    "Hạn TT",
    "Trạng thái",
]


def generate_47_invoice_rows() -> list[list[Any]]:
    """Generate 47 valid rows matching DOC-02 spec."""
    rows: list[list[Any]] = []
    customers = [
        ("Công ty Cổ phần Giáo dục Việt Nam", "0309876543"),
        ("Công ty TNHH TechSoft", "0305551234"),
        ("Công ty TNHH Giải pháp Số", "0304445678"),
        ("Công ty Cổ phần Văn phòng Phẩm", "0301112223"),
        ("Công ty TNHH Minh Phát", "0306667778"),
        ("Công ty Cổ phần ABC Retail", "0302223334"),
        ("Công ty TNHH Đại Lợi", "0307778889"),
        ("Công ty TNHH An Khang", "0308889990"),
        ("Công ty TNHH FPT Trading", "0303334445"),
        ("Công ty Cổ phần Thương mại Quốc tế", "0305556677"),
        ("Công ty Cổ phần TechVN", "0301119988"),
        ("Công ty TNHH Đầu tư Đại Cường", "0302228877"),
        ("Công ty TNHH Thương mại Lộc Phát", "0303332211"),
        ("Công ty Cổ phần Bút Tre VN", "0304443322"),
    ]
    for i in range(1, 48):
        c_name, c_tax = customers[(i - 1) % len(customers)]
        subtotal = 100_000_000 + (i * 5_000_000)
        paid = subtotal if i % 2 == 0 else 0
        status_val = "PAID" if paid > 0 else "UNPAID"
        rows.append(
            [
                i,
                f"HV-{i:03d}",
                f"{min(i, 28):02d}/09/2026",
                c_name,
                c_tax,
                subtotal,
                "10%",
                paid,
                f"{min(i, 28):02d}/10/2026",
                status_val,
            ]
        )
    return rows


# ---------------------------------------------------------------------------
# TC-IDP-007 Tests
# ---------------------------------------------------------------------------


def test_tc_idp_007_excel_47_rows_mapping_suggestion_and_confirm(
    app_client: TestClient,
    seed_test_users: dict[str, tuple[User, str]],
    db_session: Session,
) -> None:
    """TC-IDP-007 Part 1: EP-23 47 rows -> mapping_suggestion; EP-36 confirm -> 47 record groups."""
    _, cfo_token = seed_test_users["ROLE-02"]
    headers = {"Authorization": f"Bearer {cfo_token}"}

    rows_47 = generate_47_invoice_rows()
    assert len(rows_47) == 47
    xlsx_bytes = make_test_xlsx_bytes(DOC_02_HEADERS, rows_47)
    mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    # 1. EP-23: Upload Excel 47 rows
    resp_upload = app_client.post(
        "/api/v1/documents/import",
        headers=headers,
        data={"doc_type": "INVOICE"},
        files={"file": ("DOC-02-invoices.xlsx", io.BytesIO(xlsx_bytes), mime)},
    )
    assert resp_upload.status_code == 201, resp_upload.text
    data = resp_upload.json()["data"]
    meta = resp_upload.json().get("meta", {})
    doc_id = UUID(data["id"])

    assert data["kind"] == "FILE"
    assert data["channel"] == "C5"
    assert data["status"] == "UPLOADED"

    # Verify mapping suggestions
    assert "mapping_suggestion" in meta
    suggestion = meta["mapping_suggestion"]
    assert suggestion["sheet_name"] == "Sheet1"
    assert suggestion["header_row"] == 1
    cols = suggestion["columns"]
    assert len(cols) == len(DOC_02_HEADERS)

    col_map = {c["column"]: c for c in cols}
    assert col_map["B"]["suggested_field_key"] == "invoice_number"
    assert col_map["C"]["suggested_field_key"] == "issue_date"
    assert col_map["D"]["suggested_field_key"] == "customer_name"
    assert col_map["E"]["suggested_field_key"] == "customer_tax_code"
    assert col_map["F"]["suggested_field_key"] == "subtotal"
    assert col_map["G"]["suggested_field_key"] == "vat_rate"
    assert col_map["H"]["suggested_field_key"] == "paid_amount"
    assert col_map["I"]["suggested_field_key"] == "due_date"
    assert col_map["J"]["suggested_field_key"] == "status"

    # Verify audit log for import upload
    stmt_audit = select(AuditLog).where(
        AuditLog.action == "document.import_upload",
        AuditLog.target_id == doc_id,
    )
    audit_upload = db_session.execute(stmt_audit).scalar_one_or_none()
    assert audit_upload is not None

    # 2. EP-36: Confirm mapping
    confirm_payload = {
        "doc_type": "INVOICE",
        "columns": [
            {"column": "B", "field_key": "invoice_number"},
            {"column": "C", "field_key": "issue_date"},
            {"column": "D", "field_key": "customer_name"},
            {"column": "E", "field_key": "customer_tax_code"},
            {"column": "F", "field_key": "subtotal"},
            {"column": "G", "field_key": "vat_rate"},
            {"column": "H", "field_key": "paid_amount"},
            {"column": "I", "field_key": "due_date"},
            {"column": "J", "field_key": "status"},
        ],
    }
    resp_confirm = app_client.post(
        f"/api/v1/documents/{doc_id}/import-mapping",
        headers=headers,
        json=confirm_payload,
    )
    assert resp_confirm.status_code == 200, resp_confirm.text
    confirm_data = resp_confirm.json()["data"]
    assert confirm_data["status"] == "NEEDS_REVIEW"

    # Verify ExtractedFields: exactly 47 record groups
    stmt_fields = select(ExtractedField).where(ExtractedField.source_document_id == doc_id)
    fields = db_session.execute(stmt_fields).scalars().all()
    record_groups = {f.record_group for f in fields if f.record_group}
    assert len(record_groups) == 47, f"Expected 47 record groups, got {len(record_groups)}"

    # Check cell source location on each field
    for f in fields:
        assert f.source_kind == SourceLocationKind.CELL
        assert f.source_location is not None
        assert f.source_location["kind"] == "cell"
        assert f.source_location["sheet"] == "Sheet1"
        assert "row" in f.source_location
        assert "col" in f.source_location


def test_tc_idp_007_row_errors_do_not_block_valid_rows(
    app_client: TestClient,
    seed_test_users: dict[str, tuple[User, str]],
    db_session: Session,
) -> None:
    """TC-IDP-007 Part 2: Row errors report row_index without blocking valid rows (IDP-E11)."""
    _, cfo_token = seed_test_users["ROLE-02"]
    headers = {"Authorization": f"Bearer {cfo_token}"}

    rows_48 = generate_47_invoice_rows()
    # Add 1 row with invalid tax code
    rows_48.append([
        48,
        "HV-048",
        "28/09/2026",
        "Công ty Lỗi Thuế",
        "12345",  # Invalid tax code!
        50_000_000,
        "10%",
        0,
        "28/10/2026",
        "UNPAID",
    ])
    assert len(rows_48) == 48

    xlsx_bytes = make_test_xlsx_bytes(DOC_02_HEADERS, rows_48)
    mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    resp_upload = app_client.post(
        "/api/v1/documents/import",
        headers=headers,
        data={"doc_type": "INVOICE"},
        files={"file": ("invoices_with_error.xlsx", io.BytesIO(xlsx_bytes), mime)},
    )
    assert resp_upload.status_code == 201
    doc_id = UUID(resp_upload.json()["data"]["id"])

    # Confirm mapping
    confirm_payload = {
        "doc_type": "INVOICE",
        "columns": [
            {"column": "B", "field_key": "invoice_number"},
            {"column": "C", "field_key": "issue_date"},
            {"column": "D", "field_key": "customer_name"},
            {"column": "E", "field_key": "customer_tax_code"},
        ],
    }
    resp_confirm = app_client.post(
        f"/api/v1/documents/{doc_id}/import-mapping",
        headers=headers,
        json=confirm_payload,
    )
    assert resp_confirm.status_code == 200
    meta = resp_confirm.json().get("meta", {})
    row_errors = meta.get("row_errors", [])
    assert len(row_errors) >= 1
    # Check that row 49 (header=1, 48th data row is index 49) is reported
    err_rows = [e["row_index"] for e in row_errors]
    assert 49 in err_rows

    # The 47 valid rows STILL get extracted!
    stmt_fields = select(ExtractedField).where(ExtractedField.source_document_id == doc_id)
    fields = db_session.execute(stmt_fields).scalars().all()
    record_groups = {f.record_group for f in fields if f.record_group}
    assert len(record_groups) == 47


def test_tc_idp_007_exceeds_5000_rows_rejected(
    app_client: TestClient,
    seed_test_users: dict[str, tuple[User, str]],
) -> None:
    """TC-IDP-007 Part 3: Spreadsheet with > 5,000 rows returns 422 VALIDATION_ERROR."""
    _, cfo_token = seed_test_users["ROLE-02"]
    headers = {"Authorization": f"Bearer {cfo_token}"}

    # Generate CSV with 5,001 data rows
    csv_lines = ["Số HĐ,Khách hàng,MST,Tiền"]
    for i in range(5001):
        csv_lines.append(f"HD-{i},Customer {i},0101234567,1000000")
    csv_bytes = "\n".join(csv_lines).encode("utf-8")

    resp = app_client.post(
        "/api/v1/documents/import",
        headers=headers,
        data={"doc_type": "INVOICE"},
        files={"file": ("large_5001_rows.csv", io.BytesIO(csv_bytes), "text/csv")},
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"


def test_tc_idp_007_non_uploader_cannot_confirm_mapping(
    app_client: TestClient,
    seed_test_users: dict[str, tuple[User, str]],
) -> None:
    """TC-IDP-007 Part 4: Calling EP-36 from user different from uploader returns 403."""
    _, cfo_token = seed_test_users["ROLE-02"]
    _, ceo_token = seed_test_users["ROLE-01"]

    # CFO uploads
    rows = generate_47_invoice_rows()[:5]
    xlsx_bytes = make_test_xlsx_bytes(DOC_02_HEADERS, rows)
    mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    resp_upload = app_client.post(
        "/api/v1/documents/import",
        headers={"Authorization": f"Bearer {cfo_token}"},
        data={"doc_type": "INVOICE"},
        files={"file": ("doc_cfo.xlsx", io.BytesIO(xlsx_bytes), mime)},
    )
    assert resp_upload.status_code == 201
    doc_id = resp_upload.json()["data"]["id"]

    # CEO attempts to confirm mapping on CFO's upload -> 403 FORBIDDEN_SCOPE
    confirm_payload = {
        "doc_type": "INVOICE",
        "columns": [{"column": "B", "field_key": "invoice_number"}],
    }
    resp_forbidden = app_client.post(
        f"/api/v1/documents/{doc_id}/import-mapping",
        headers={"Authorization": f"Bearer {ceo_token}"},
        json=confirm_payload,
    )
    assert resp_forbidden.status_code == 403
    assert resp_forbidden.json()["error"]["code"] == "FORBIDDEN_SCOPE"


def test_tc_idp_007_reconfirming_returns_409_conflict_state(
    app_client: TestClient,
    seed_test_users: dict[str, tuple[User, str]],
) -> None:
    """TC-IDP-007 Part 5: Re-confirming already confirmed mapping returns 409 CONFLICT_STATE."""
    _, cfo_token = seed_test_users["ROLE-02"]
    headers = {"Authorization": f"Bearer {cfo_token}"}

    rows = generate_47_invoice_rows()[:5]
    xlsx_bytes = make_test_xlsx_bytes(DOC_02_HEADERS, rows)
    mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    resp_upload = app_client.post(
        "/api/v1/documents/import",
        headers=headers,
        data={"doc_type": "INVOICE"},
        files={"file": ("doc_twice.xlsx", io.BytesIO(xlsx_bytes), mime)},
    )
    assert resp_upload.status_code == 201
    doc_id = resp_upload.json()["data"]["id"]

    confirm_payload = {
        "doc_type": "INVOICE",
        "columns": [{"column": "B", "field_key": "invoice_number"}],
    }
    # First confirm -> 200 OK
    resp_first = app_client.post(
        f"/api/v1/documents/{doc_id}/import-mapping",
        headers=headers,
        json=confirm_payload,
    )
    assert resp_first.status_code == 200

    # Second confirm -> 409 CONFLICT_STATE
    resp_second = app_client.post(
        f"/api/v1/documents/{doc_id}/import-mapping",
        headers=headers,
        json=confirm_payload,
    )
    assert resp_second.status_code == 409
    assert resp_second.json()["error"]["code"] == "CONFLICT_STATE"
