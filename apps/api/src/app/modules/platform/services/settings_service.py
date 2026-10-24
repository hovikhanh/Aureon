"""Public `platform` service for `ENT-SystemSetting` (10 §4).

The only cross-module entry point for reading/writing a non-secret system setting
(`platform.system_settings`). Other modules (e.g. `ai` kill switch) call this instead of
importing the `platform` model (DEC-125). The DB `no_secrets_in_db` CK keeps secrets out.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.platform.models import SystemSetting


@dataclass(frozen=True)
class SettingRow:
    value: dict[str, Any]
    updated_by: uuid.UUID | None
    updated_at: datetime | None
    reason: str | None = None
    version: int = 1


class SystemSettingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, key: str) -> SettingRow | None:
        row = await self._row(key)
        if row is None:
            return None
        return SettingRow(value=dict(row.value or {}), updated_by=row.updated_by,
                          updated_at=row.updated_at, reason=row.updated_reason,
                          version=row.version)  # fmt: skip

    async def set(
        self, key: str, value: dict[str, Any], *, reason: str, updated_by: uuid.UUID
    ) -> SettingRow:
        row = await self._row(key)
        if row is None:
            row = SystemSetting(
                key=key, value=value, is_secret=False, updated_reason=reason,
                updated_by=updated_by,
            )  # fmt: skip
            self.db.add(row)
        else:
            row.value = value
            row.updated_reason = reason
            row.updated_by = updated_by
            row.updated_at = datetime.now(UTC)
            row.version = row.version + 1
        await self.db.flush()
        return SettingRow(value=dict(value), updated_by=updated_by, updated_at=row.updated_at,
                          reason=reason, version=row.version or 1)  # fmt: skip

    async def id_of(self, key: str) -> uuid.UUID:
        row = await self._row(key)
        if row is None:
            raise LookupError(key)
        return row.id

    async def _row(self, key: str) -> SystemSetting | None:
        return (
            await self.db.execute(select(SystemSetting).where(SystemSetting.key == key))
        ).scalar_one_or_none()
