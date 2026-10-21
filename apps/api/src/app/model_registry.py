"""Every module's models, imported so `Base.metadata` is complete.

Used only by Alembic (`env.py`) and tests. Kept outside `core/` because `core/` must not
import `modules/` (CLAUDE.md §4.3).
"""

from types import ModuleType

from app.core.base_model import Base
from app.modules.ai import models as ai_models
from app.modules.auth import models as auth_models
from app.modules.execution import models as execution_models
from app.modules.finance import models as finance_models
from app.modules.hr import models as hr_models
from app.modules.idp import models as idp_models
from app.modules.platform import models as platform_models
from app.modules.product import models as product_models
from app.modules.risk import models as risk_models
from app.modules.sales import models as sales_models

# 05 §12.1 G2 order. `dashboard` has no schema (DEC-125).
SCHEMAS: tuple[str, ...] = (
    "platform", "auth", "hr", "finance", "sales", "product", "risk", "execution", "idp", "ai",
)  # fmt: skip

MODEL_MODULES: dict[str, ModuleType] = {
    "platform": platform_models,
    "auth": auth_models,
    "hr": hr_models,
    "finance": finance_models,
    "sales": sales_models,
    "product": product_models,
    "risk": risk_models,
    "execution": execution_models,
    "idp": idp_models,
    "ai": ai_models,
}

metadata = Base.metadata
