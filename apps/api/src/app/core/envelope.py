"""Success envelope `{ data, meta? }` (10 §1.3, DEC-130).

Routes do not build the envelope: `EnvelopeRoute` (core/routing.py) wraps the declared
`response_model` in `Envelope[...]` and the returned value in `Envelope(data=..., meta=...)`.
Return a `Page` from list endpoints to get `meta.pagination`.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from pydantic import BaseModel

from app.core.request_context import current_request_id


class Pagination(BaseModel):
    total: int
    limit: int
    offset: int
    has_next: bool


class Meta(BaseModel):
    request_id: str | None = None
    generated_at: datetime | None = None
    pagination: Pagination | None = None


class Envelope[T](BaseModel):
    data: T
    meta: Meta | None = None


@dataclass(frozen=True)
class Page[T]:
    """List result: `items` → `data`, the rest → `meta.pagination`."""

    items: Sequence[T]
    total: int
    limit: int
    offset: int


def page_meta(*, total: int, limit: int, offset: int) -> Pagination:
    return Pagination(total=total, limit=limit, offset=offset, has_next=offset + limit < total)


def build_meta(pagination: Pagination | None = None) -> Meta:
    return Meta(
        request_id=current_request_id(),
        generated_at=datetime.now(UTC),
        pagination=pagination,
    )


def to_envelope(result: object) -> object:
    """Wrap an endpoint's return value. Already-wrapped values pass through."""
    if isinstance(result, Envelope):
        return result
    if isinstance(result, Page):
        pagination = page_meta(total=result.total, limit=result.limit, offset=result.offset)
        return Envelope[object](data=list(result.items), meta=build_meta(pagination))
    return Envelope[object](data=result, meta=build_meta())
