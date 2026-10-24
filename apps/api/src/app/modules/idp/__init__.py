"""Module `idp` (schema `idp`).

Registers the onboarding org-import commit reader of `core/onboarding.py` (05 §2.8: step
`review` is done once the `org_import` C5 document commits).
"""

from app.core.onboarding import register_import_committed
from app.modules.idp.services.onboarding_import import import_committed_at

register_import_committed(import_committed_at)
