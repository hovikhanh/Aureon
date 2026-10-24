"""Module `hr` (schema `hr`).

Registers the department-subtree provider of `core/org_scope.py` (R-DEC-57, T-632) so modules
that may not import `hr` (`execution`) can resolve "department + sub-departments".
"""

from app.core.org_scope import register_subtree_provider
from app.modules.hr.services.structure_service import department_subtree

register_subtree_provider(department_subtree)
