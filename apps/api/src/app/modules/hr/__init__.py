"""Module `hr` (schema `hr`).

Registers the department-subtree provider of `core/org_scope.py` (R-DEC-57, T-632) so modules
that may not import `hr` (`execution`) can resolve "department + sub-departments", and the
onboarding `progress` source of `core/onboarding.py` (EP-ADM-13, R-DEC-75).
"""

from app.core.onboarding import register_progress_source
from app.core.org_scope import register_subtree_provider
from app.modules.hr.services.onboarding_progress import hr_progress
from app.modules.hr.services.structure_service import department_subtree

register_subtree_provider(department_subtree)
register_progress_source("hr", hr_progress)
