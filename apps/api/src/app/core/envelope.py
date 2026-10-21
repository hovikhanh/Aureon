"""Success envelope `{ data, meta? }` (10 §1.3, DEC-130).

Routes declare `response_model=Envelope[X]` (so OpenAPI shows the real contract) and return
`ok(x)`. Errors never go through here — see `core/handlers.py`.
"""

from pydantic import BaseModel


class Pagination(BaseModel):
    total: int
    limit: int
    offset: int
    has_next: bool


class Meta(BaseModel):
    pagination: Pagination | None = None


class Envelope[T](BaseModel):
    data: T
    meta: Meta | None = None


def ok[T](data: T, meta: Meta | None = None) -> Envelope[T]:
    return Envelope[T](data=data, meta=meta)


def page_meta(*, total: int, limit: int, offset: int) -> Meta:
    has_next = offset + limit < total
    return Meta(pagination=Pagination(total=total, limit=limit, offset=offset, has_next=has_next))
