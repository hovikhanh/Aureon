"""Success envelope — 10 §1.2 (`{ data, meta? }`) and list meta — 10 §1.5. T-005.

Usage in an endpoint (always declare `response_model`, CLAUDE.md § API):

    @router.get("/things/{id}", response_model=Envelope[ThingOut])
    def get_thing(...) -> Envelope[ThingOut]:
        return Envelope(data=ThingOut(...))

    @router.get("/things", response_model=Page[ThingOut])
    def list_things(params: Annotated[PageParams, Depends(get_page_params)]) -> Page[ThingOut]:
        return Page.build(items, params=params, total=total)   # see core/pagination.py
"""

from typing import Any

from pydantic import BaseModel, Field


class PageMeta(BaseModel):
    """`meta` of every list endpoint — 10 §1.5."""

    page: int
    page_size: int
    total: int
    total_pages: int


class Envelope[T](BaseModel):
    """`{ "data": T, "meta"?: {...} }`. `meta` is omitted from JSON when not set (10 §1.2)."""

    data: T
    meta: dict[str, Any] | None = Field(default=None, exclude_if=lambda v: v is None)


class Page[T](BaseModel):
    """Paginated list envelope: `{ "data": [T], "meta": PageMeta }` — 10 §1.5."""

    data: list[T]
    meta: PageMeta
