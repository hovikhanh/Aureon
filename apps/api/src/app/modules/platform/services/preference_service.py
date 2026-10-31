"""User preference store (R-DEC-87, M2.1) — public service for `dashboard` reporting.

Key `dashboard.executive_tiles` = JSON mảng ≤ 4 metric_code (4 ô Executive). Validate mã ∈
catalog + trong scope người lưu (scope do caller cung cấp qua `in_scope`); version optimistic.
"""

import uuid
from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.deps import Principal
from app.core.errors import BusinessRuleError, ConflictStateError, ValidationError
from app.modules.platform.models import UserPreference
from app.modules.platform.repositories import UserPreferenceRepository
from app.modules.platform.services.catalog import BY_CODE

TILES_KEY = "dashboard.executive_tiles"
DEFAULT_EXECUTIVE_TILES = [
    "METRIC-FIN-01", "METRIC-FIN-03", "METRIC-STR-01", "METRIC-OPS-01",
]  # fmt: skip
MAX_TILES = 4


class UserPreferenceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = UserPreferenceRepository(db)

    async def _row(self, user: Principal, key: str) -> UserPreference | None:
        return await self.repo.by_key(user.user_id, key)

    async def executive_tiles(self, user: Principal) -> tuple[list[str], int]:
        """Current tiles + version; no row → code default (R-DEC-87), version 0."""
        row = await self._row(user, TILES_KEY)
        if row is None:
            return list(DEFAULT_EXECUTIVE_TILES), 0
        return list(row.value_json), row.version

    async def set_executive_tiles(
        self, user: Principal, tiles: list[str], version: int,
        in_scope: Callable[[str], bool],
    ) -> tuple[list[str], int]:  # fmt: skip
        if len(tiles) > MAX_TILES:
            raise ValidationError(f"at most {MAX_TILES} tiles", details={"field": "tiles"})
        if len(set(tiles)) != len(tiles):
            raise ValidationError("duplicate tile", details={"field": "tiles"})
        for code in tiles:
            if code not in BY_CODE:
                raise ValidationError("unknown metric", details={"metric_code": code})
            if not in_scope(code):
                raise BusinessRuleError(
                    "metric outside your scope",
                    details={"metric_code": code, "reason": "out_of_scope"},
                )
        row = await self._row(user, TILES_KEY)
        if row is None:
            if version != 0:
                raise ConflictStateError("version mismatch", details={"expected": "0"})
            row = UserPreference(
                id=uuid.uuid4(), tenant_id=user.tenant_id, user_id=user.user_id,
                key=TILES_KEY, value_json=list(tiles), version=1,
            )
            self.db.add(row)
            new_version = 1
        else:
            if row.version != version:
                raise ConflictStateError(
                    "version mismatch", details={"expected": str(row.version)}
                )
            row.value_json = list(tiles)
            row.version = version + 1
            new_version = row.version
        await record_audit(
            self.db, action="platform.preference_update",
            target_schema="platform", target_table="user_preferences", target_id=row.id,
            after={"key": TILES_KEY, "tiles": tiles}, metadata={"key": TILES_KEY},
        )
        await self.db.flush()
        return list(tiles), new_version
