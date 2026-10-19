"""Model registry: importing this module registers every entity on ``Base.metadata``.

Imported by Alembic ``env.py`` (autogenerate / ``alembic check``) and by the seed, so the
metadata is complete regardless of which feature module is imported first. Add each new
entity module here (T-201, T-301, ...).
"""

from sqlalchemy import MetaData

from app.db.base import Base
from app.modules.audit.models import AuditLog
from app.modules.auth.models import Role, User
from app.modules.dashboard.models import Alert, Metric, MetricValue
from app.modules.idp.models import (
    BusinessRecord,
    DocumentPage,
    ExtractedField,
    ExtractionJob,
    ExtractionReview,
    SourceDocument,
)

#: Complete metadata (all entities registered) — Alembic's ``target_metadata``.
metadata: MetaData = Base.metadata

__all__ = [
    "Alert",
    "AuditLog",
    "BusinessRecord",
    "DocumentPage",
    "ExtractedField",
    "ExtractionJob",
    "ExtractionReview",
    "Metric",
    "MetricValue",
    "Role",
    "SourceDocument",
    "User",
    "metadata",
]
