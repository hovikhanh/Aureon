"""HTTP routes for `product` — EP-90..95 (10 §3.9, §4.9, §5).

Route files register on the shared `deps.router`; importing them here wires every endpoint.
"""

from app.modules.product.routes import catalog, planning
from app.modules.product.routes.deps import router

__all__ = ["catalog", "planning", "router"]
