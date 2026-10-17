"""Pagination — 10 §1.5 (`page` ≥ 1 default 1, `page_size` 1..100 default 20). T-005, TC-SYS-006.

Out-of-range values return `400 BAD_REQUEST` (TC-SYS-006), never 422: query-parameter validation
errors are mapped to BAD_REQUEST by `core.handlers` (10 §1.3: "tham số không hợp lệ").

    @router.get("/documents", response_model=Page[DocumentOut])
    def list_documents(
        params: Annotated[PageParams, Depends(get_page_params)],
    ) -> Page[DocumentOut]:
        rows = query.offset(params.offset).limit(params.limit).all()
        return paginate(rows, params=params, total=total)
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Annotated

from fastapi import Query

from app.core.envelope import Page, PageMeta

DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


@dataclass(frozen=True, slots=True)
class PageParams:
    page: int = DEFAULT_PAGE
    page_size: int = DEFAULT_PAGE_SIZE

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


def get_page_params(
    page: Annotated[int, Query(ge=1, description="1-based page number (10 §1.5)")] = DEFAULT_PAGE,
    page_size: Annotated[
        int, Query(ge=1, le=MAX_PAGE_SIZE, description="Items per page, 1..100 (10 §1.5)")
    ] = DEFAULT_PAGE_SIZE,
) -> PageParams:
    """FastAPI dependency: `params: Annotated[PageParams, Depends(get_page_params)]`."""
    return PageParams(page=page, page_size=page_size)


def build_page_meta(params: PageParams, total: int) -> PageMeta:
    """`{page, page_size, total, total_pages}`; `total_pages` is 0 when `total` is 0."""
    return PageMeta(
        page=params.page,
        page_size=params.page_size,
        total=total,
        total_pages=math.ceil(total / params.page_size) if total > 0 else 0,
    )


def paginate[T](items: Sequence[T], *, params: PageParams, total: int) -> Page[T]:
    """Wrap one already-sliced page of items into the list envelope."""
    return Page[T](data=list(items), meta=build_page_meta(params, total))
