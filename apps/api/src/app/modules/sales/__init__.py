"""Module `sales` (schema `sales`).

Registers the client lookup of `core/client_directory.py` (R-DEC-172) so `finance` can link an
OUT invoice to its client from the customer's tax code without importing `sales`, and the target
lookup of `core/revenue_target.py` (METRIC-FIN-01 on the finance dashboard), same reason.
"""

from app.core.client_directory import register_client_lookup
from app.core.revenue_target import register_revenue_target
from app.modules.sales.services.sales_service import client_ref_by_tax_code, team_revenue_target

register_client_lookup(client_ref_by_tax_code)
register_revenue_target(team_revenue_target)
