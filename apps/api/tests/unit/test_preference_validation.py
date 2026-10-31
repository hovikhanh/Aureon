"""TC-M21-07 (unit) — validate 4 ô Executive (R-DEC-87): quá 4, trùng, mã lạ, ngoài scope.

Các nhánh lỗi raise TRƯỚC khi chạm DB, nên db giả (không bao giờ query) là đủ cho unit test.
"""

import uuid

import pytest

from app.core.deps import Principal
from app.core.errors import BusinessRuleError, ValidationError
from app.modules.platform.services.preference_service import (
    DEFAULT_EXECUTIVE_TILES,
    MAX_TILES,
    UserPreferenceService,
)

_TENANT = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _ceo() -> Principal:
    return Principal(
        user_id=uuid.uuid4(), role="CEO", permissions=frozenset({"dashboard:write"}),
        tenant_id=_TENANT,
    )


def _svc() -> UserPreferenceService:
    return UserPreferenceService(db=object())  # type: ignore[arg-type]


def _always(_: str) -> bool:
    return True


async def test_too_many_tiles() -> None:
    tiles = ["METRIC-FIN-01", "METRIC-FIN-02", "METRIC-FIN-03", "METRIC-OPS-01", "METRIC-STR-01"]
    assert len(tiles) > MAX_TILES
    with pytest.raises(ValidationError):
        await _svc().set_executive_tiles(_ceo(), tiles, 0, _always)


async def test_duplicate_tile() -> None:
    with pytest.raises(ValidationError):
        await _svc().set_executive_tiles(_ceo(), ["METRIC-FIN-01", "METRIC-FIN-01"], 0, _always)


async def test_unknown_code() -> None:
    with pytest.raises(ValidationError):
        await _svc().set_executive_tiles(_ceo(), ["METRIC-XXX-99"], 0, _always)


async def test_out_of_scope_is_business_rule() -> None:
    with pytest.raises(BusinessRuleError) as exc:
        await _svc().set_executive_tiles(_ceo(), ["METRIC-FIN-01"], 0, lambda _c: False)
    assert exc.value.details.get("reason") == "out_of_scope"


def test_default_tiles_are_four_valid_codes() -> None:
    from app.modules.platform.services.catalog import BY_CODE

    assert len(DEFAULT_EXECUTIVE_TILES) == MAX_TILES
    assert all(c in BY_CODE for c in DEFAULT_EXECUTIVE_TILES)
