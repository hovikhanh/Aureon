"""P0 doc-type seed catalog (T-634): data only. The DB (`idp.document_types`,
`extraction_schemas`, `validation_rules`) is the source of truth at runtime; Admin edits it
via EP-DC-27..35. Migration 0019 and `schema_registry.ensure_*` seed from these dicts.
"""

from app.modules.idp.services.catalog.goals import PERIOD_REPORT, PLAN_KPI_OKR
from app.modules.idp.services.catalog.org import HR_ROSTER

SEED_TYPES = (PLAN_KPI_OKR, PERIOD_REPORT, HR_ROSTER)

__all__ = ["HR_ROSTER", "PERIOD_REPORT", "PLAN_KPI_OKR", "SEED_TYPES"]
