"""hr: pgcrypto column encryption for level-4 PII (NĐ 13/2023, 05 OQ-08) — T-234, DEC-207

Revision ID: 0008_pgcrypto
Revises: 0007_audit_writer_role
Create Date: 2026-10-22

`hr.employees.national_id`, `hr.employees.bank_account` (text) and
`hr.salary_history.base_salary` (bigint) become `bytea` = `pgp_sym_encrypt(value::text, key)`.
Existing rows are converted in place with the key from `DB_ENCRYPTION_KEY`; the key is passed
as a bound parameter, never in literal SQL. `base_salary > 0` moves to the service (a CHECK
cannot read ciphertext). Downgrade decrypts back to the original types.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.core.crypto_columns import encryption_key

revision: str = "0008_pgcrypto"
down_revision: str | Sequence[str] | None = "0007_audit_writer_role"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

COLUMNS = (("employees", "national_id", "text"), ("employees", "bank_account", "text"),
           ("salary_history", "base_salary", "bigint"))  # fmt: skip


def _set_key() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.get_bind().execute(
        sa.text("SELECT set_config('aureon.pii_key', :k, true)"), {"k": encryption_key()}
    )


def upgrade() -> None:
    _set_key()
    op.drop_constraint("ck_salary_history_base_salary_positive", "salary_history", schema="hr")
    for table, col, _ in COLUMNS:
        op.execute(
            f"ALTER TABLE hr.{table} ALTER COLUMN {col} TYPE bytea USING "
            f"pgp_sym_encrypt({col}::text, current_setting('aureon.pii_key'))"
        )


def downgrade() -> None:
    _set_key()
    for table, col, typ in COLUMNS:
        op.execute(
            f"ALTER TABLE hr.{table} ALTER COLUMN {col} TYPE {typ} USING "
            f"pgp_sym_decrypt({col}, current_setting('aureon.pii_key'))::{typ}"
        )
    op.create_check_constraint(
        "base_salary_positive", "salary_history", "base_salary > 0", schema="hr"
    )
