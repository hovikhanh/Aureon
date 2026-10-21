"""`limit` / `offset` / `sort_by` / `order` query params (10 §1.5, DEC-130).

Out-of-range values are `400 BAD_REQUEST` (10 §1.5: "> 100 → 400"), not FastAPI's 422.
Usage: `params: Annotated[PageParams, Depends(page_params("created_at", "amount"))]`.
"""

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Annotated, Any, Literal, cast

from fastapi import Query

from app.core.errors import BadRequestError

DEFAULT_LIMIT = 20
MAX_LIMIT = 100
DEFAULT_SORT = "created_at"

Order = Literal["asc", "desc"]


@dataclass(frozen=True)
class PageParams:
    limit: int = DEFAULT_LIMIT
    offset: int = 0
    sort_by: str = DEFAULT_SORT
    order: Order = "desc"


def page_params(*sortable: str) -> Callable[..., Coroutine[Any, Any, PageParams]]:
    """Build the dependency; `sortable` is the endpoint's `sort_by` whitelist."""
    allowed = frozenset(sortable) | {DEFAULT_SORT}

    async def _dep(
        limit: Annotated[int, Query()] = DEFAULT_LIMIT,
        offset: Annotated[int, Query()] = 0,
        sort_by: Annotated[str, Query()] = DEFAULT_SORT,
        order: Annotated[str, Query()] = "desc",
    ) -> PageParams:
        if not 1 <= limit <= MAX_LIMIT:
            raise BadRequestError(
                f"limit must be 1..{MAX_LIMIT}", details={"param": "limit", "max": MAX_LIMIT}
            )
        if offset < 0:
            raise BadRequestError("offset must be >= 0", details={"param": "offset"})
        if sort_by not in allowed:
            raise BadRequestError(
                "sort_by not allowed", details={"param": "sort_by", "allowed": sorted(allowed)}
            )
        if order not in ("asc", "desc"):
            raise BadRequestError("order must be asc|desc", details={"param": "order"})
        return PageParams(limit=limit, offset=offset, sort_by=sort_by, order=cast(Order, order))

    return _dep
