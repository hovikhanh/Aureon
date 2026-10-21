"""TC-HR-010 (T-234, DEC-207): level-4 PII columns encrypted at rest with pgcrypto.

1. raw table / `pg_dump` view: ciphertext (`bytea` PGP message), plaintext absent.
2. service + API read: plaintext; aggregates (payroll SUM) still correct.
3. PII scanner still rejects the decrypted values (outbox) and masks them (audit).
"""

import uuid
from datetime import date

import pytest
from psycopg import sql
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto_columns import encryption_key
from app.core.events.outbox import PIIDetectedError, publish_in_tx
from app.core.pii import scan_payload
from app.modules.hr.models import Employee, SalaryHistory
from app.modules.hr.repositories import SalaryRepository
from tests.conftest import ApiClient
from tests.integration.hr.helpers import make_department, make_employee

CCCD, BANK, SALARY = "079090001234", "0123456789012", 31_500_000


async def _setup(api: ApiClient) -> str:
    dept = await make_department(api)
    emp = await make_employee(api, dept["id"])
    r = await api.call("POST", f"/hr/employees/{emp['id']}/salary-history", "HR_MANAGER",
                       json={"effective_date": "2036-01-01", "base_salary": SALARY})  # fmt: skip
    assert r.status_code == 201, r.text
    return str(emp["id"])


async def test_ciphertext_at_rest(api: ApiClient, db_session: AsyncSession) -> None:
    emp_id = await _setup(api)
    raw = (await db_session.execute(text(
        "SELECT e.national_id, e.bank_account, s.base_salary, pg_typeof(s.base_salary)::text "
        "FROM hr.employees e JOIN hr.salary_history s ON s.employee_id = e.id WHERE e.id = :i"
    ), {"i": emp_id})).one()  # fmt: skip
    nid, bank, sal, typ = raw
    assert typ == "bytea"
    for blob, plain in ((nid, CCCD), (bank, BANK), (sal, str(SALARY))):
        assert isinstance(blob, bytes) and plain.encode() not in blob
        assert blob[:1] == b"\xc3"  # OpenPGP symmetric-key encrypted session key packet
    # wrong key cannot decrypt
    with pytest.raises(Exception, match=r"Wrong key|corrupt"):
        async with db_session.begin_nested():
            await db_session.execute(
                text("SELECT pgp_sym_decrypt(:b, 'not-the-key')"), {"b": bytes(nid)}
            )


async def test_dump_path_shows_ciphertext(api: ApiClient, db_session: AsyncSession) -> None:
    """`COPY … TO STDOUT` is what `pg_dump` emits for data: no plaintext, `\\x` bytea."""
    emp_id = await _setup(api)
    conn = await db_session.connection()
    raw = await conn.get_raw_connection()
    pg = raw.driver_connection
    assert pg is not None
    dump = ""
    eid = uuid.UUID(emp_id)  # validated UUID → safe to inline into COPY (no bind params)
    for table, cols, key in (("employees", "national_id, bank_account", "id"),
                             ("salary_history", "base_salary", "employee_id")):  # fmt: skip
        q = sql.SQL("COPY (SELECT {} FROM hr.{} WHERE {} = {}) TO STDOUT").format(
            sql.SQL(cols), sql.Identifier(table), sql.Identifier(key), sql.Literal(str(eid))
        )
        async with pg.cursor() as cur, cur.copy(q) as copy:
            async for chunk in copy:
                dump += bytes(chunk).decode()
    assert dump.count("\\\\x") == 3
    assert CCCD not in dump and BANK not in dump and str(SALARY) not in dump


async def test_service_reads_plaintext(api: ApiClient, db_session: AsyncSession) -> None:
    emp_id = await _setup(api)
    d = (await api.call("GET", f"/hr/employees/{emp_id}", "HR_MANAGER")).json()["data"]
    assert d["national_id"] == CCCD and d["bank_account"] == BANK
    s = await api.call("GET", f"/hr/employees/{emp_id}/salary-history", "HR_MANAGER")
    assert s.json()["data"][0]["base_salary"] == SALARY
    e = (
        await db_session.execute(select(Employee).where(Employee.id == uuid.UUID(emp_id)))
    ).scalar_one()
    assert e.national_id == CCCD
    row = (await db_session.execute(
        select(SalaryHistory.base_salary).where(SalaryHistory.employee_id == uuid.UUID(emp_id))
    )).scalar_one()  # fmt: skip
    assert row == SALARY
    total = await SalaryRepository(db_session).payroll_on(
        date(2036, 2, 1), [Employee.id == uuid.UUID(emp_id)]
    )
    assert total == SALARY
    assert len(encryption_key()) == 64


async def test_pii_scanner_still_rejects(db_session: AsyncSession) -> None:
    hits = scan_payload({"note": f"CCCD {CCCD}, TK {BANK}", "national_id": CCCD},
                        forbidden_keys=frozenset({"national_id"}))  # fmt: skip
    assert {h.type for h in hits} >= {"CCCD", "FIELD"} and len(hits) == 3  # bank no. → PHONE/BANK
    assert all(CCCD not in h.value_masked and BANK not in h.value_masked for h in hits)
    with pytest.raises(PIIDetectedError):
        await publish_in_tx(
            db_session, event_type="hr.hiring_plan_delayed", producer="hr",
            aggregate_schema="hr", aggregate_table="hiring_plans", aggregate_id=uuid.uuid4(),
            payload={"employee_id": str(uuid.uuid4()), "memo": f"cccd {CCCD}"},
        )  # fmt: skip
