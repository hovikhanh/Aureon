"""Module `sales` (schema `sales`).

Registers the client lookup of `core/client_directory.py` (R-DEC-172) so `finance` can link an
OUT invoice to its client from the customer's tax code without importing `sales`.
"""

from app.core.client_directory import register_client_lookup
from app.modules.sales.services.sales_service import client_ref_by_tax_code

register_client_lookup(client_ref_by_tax_code)
