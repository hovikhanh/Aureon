"""DB role app_audit_writer: INSERT, SELECT only on platform.audit_logs (05 ENT-AuditLog)

Revision ID: 0007_audit_writer_role
Revises: 0006_extraction_schema_version
Create Date: 2026-10-21

05: "app DB user chỉ có `INSERT, SELECT`; trigger chặn UPDATE/DELETE". The trigger exists since
0001. This adds the privilege layer as a NOLOGIN group role (defense in depth): the app still
connects with the shared role in S0 (05 §12 G4 — per-module DB roles come later), so the
trigger + ORM guard remain the enforcing layers. A role is a cluster-level object, not a schema
change: no table/column is touched.

Every migration must be reversible (05 §12.1 G3): implement both upgrade() and downgrade().
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0007_audit_writer_role"
down_revision: str | Sequence[str] | None = "0006_extraction_schema_version"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Literal SQL (no interpolation) — role name is fixed.
CREATE_ROLE = """
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_audit_writer') THEN
        CREATE ROLE app_audit_writer NOLOGIN;
    END IF;
END
$$
"""


def upgrade() -> None:
    # Idempotent: roles are cluster-wide and may survive a `downgrade base` of another DB.
    op.execute(CREATE_ROLE)
    op.execute("GRANT USAGE ON SCHEMA platform TO app_audit_writer")
    op.execute("REVOKE ALL ON platform.audit_logs FROM app_audit_writer")
    op.execute("GRANT INSERT, SELECT ON platform.audit_logs TO app_audit_writer")


def downgrade() -> None:
    op.execute("REVOKE ALL ON platform.audit_logs FROM app_audit_writer")
    op.execute("REVOKE USAGE ON SCHEMA platform FROM app_audit_writer")
    op.execute("DROP ROLE IF EXISTS app_audit_writer")
