"""TC-M12-12 (T-615, R-DEC-34) — field-policy registry is the single source for masking."""

import re
from dataclasses import dataclass, field

from app.core.audit import MASKED_KEYS, mask
from app.core.events.outbox import FORBIDDEN_PAYLOAD_KEYS
from app.core.field_policy import (
    FIELD_POLICY,
    LEVEL3_KEYS,
    LEVEL4_KEYS,
    SENSITIVE_KEYS,
    Masked,
    mask_fields,
    strip_for_model,
)

# Field names that look sensitive (02 §5.3) — any of them in an API schema must be declared.
_SUSPICIOUS = re.compile(
    r"(salary|date_of_birth|^dob$|address|national_id|cccd|bank_account|emergency|email|phone|"
    r"tax_code)",
)
# Request bodies / auth plumbing are not response data (credentials are never serialised out).
_NOT_DATA = {"LoginIn", "TokenOut", "RefreshIn"}


@dataclass(frozen=True)
class P:
    role: str
    scope_pillars: frozenset[str] = field(default_factory=frozenset)


CEO, HR_DIR, FIN_DIR = P("CEO"), P("DIR", frozenset({"O"})), P("DIR", frozenset({"F"}))
ADM, MGR, EMP = P("ADM"), P("MGR"), P("EMP")
ROW = {"full_name": "Nguyễn Văn An", "email": "an@abc.test", "phone": "0901234567",
       "date_of_birth": "1990-05-01", "national_id": "079090001234"}  # fmt: skip


def test_levels_and_audiences() -> None:
    assert LEVEL4_KEYS == {"date_of_birth", "address", "national_id", "bank_account",
                           "emergency_contact", "base_salary"}  # fmt: skip
    assert LEVEL3_KEYS == {"email", "phone"}
    assert SENSITIVE_KEYS <= MASKED_KEYS and SENSITIVE_KEYS <= FORBIDDEN_PAYLOAD_KEYS


def test_mask_fields_per_role() -> None:
    for user in (CEO, HR_DIR):
        assert mask_fields("hr.employees", user, ROW) == ROW
    for user in (FIN_DIR, MGR, EMP):
        out = mask_fields("hr.employees", user, ROW)
        assert out["date_of_birth"] == Masked() and out["national_id"] == Masked()
        assert out["email"] == ROW["email"] and out["full_name"] == ROW["full_name"]
    adm = mask_fields("hr.employees", ADM, ROW)
    assert adm["email"] == Masked() and adm["phone"] == Masked() and adm["full_name"]
    assert mask_fields("hr.employees", None, ROW) == ROW  # internal (audit) view


def test_audit_masks_the_same_list() -> None:
    masked = mask(ROW)
    assert all(masked[k] == "••••" for k in ("email", "phone", "date_of_birth", "national_id"))
    assert masked["full_name"] == "Nguyễn Văn An"


def test_strip_for_model() -> None:
    out = strip_for_model({"employees": [ROW], "contacts": [{"email": "k@client.vn"}]},
                          client_keys=("contacts",))  # fmt: skip
    emp = out["employees"][0]
    assert "date_of_birth" not in emp and "national_id" not in emp
    assert emp["email"].startswith("EMP-") and emp["phone"].startswith("EMP-")
    assert out["contacts"][0]["email"].startswith("CLI-")
    assert strip_for_model({"x": ROW})["x"]["email"] == emp["email"]  # stable pseudonym


def test_no_sensitive_field_outside_registry() -> None:
    from app.main import create_app

    declared = {r.field for r in FIELD_POLICY}
    schemas = create_app().openapi()["components"]["schemas"]
    leaks = [
        f"{name}.{prop}"
        for name, sch in schemas.items()
        if name not in _NOT_DATA
        for prop in sch.get("properties", {})
        if _SUSPICIOUS.search(prop) and prop not in declared
    ]
    assert leaks == [], f"declare in core/field_policy.py: {leaks}"
