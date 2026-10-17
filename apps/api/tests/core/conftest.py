"""Test app for T-005: create_app() + test-only routes exercising core API infra."""

from collections.abc import Iterator
from typing import Annotated

import pytest
from fastapi import APIRouter, Depends, FastAPI, Response
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.envelope import Envelope, Page
from app.core.errors import ApiError, ErrorCode
from app.core.idempotency import (
    Idempotency,
    InMemoryIdempotencyStore,
    get_idempotency_store,
    optional_idempotency,
    require_idempotency,
)
from app.core.pagination import PageParams, get_page_params, paginate
from app.main import API_PREFIX, create_app


class ItemIn(BaseModel):
    name: str
    qty: int


class ItemOut(BaseModel):
    id: int
    name: str
    qty: int


ITEMS = [ItemOut(id=i, name=f"item-{i}", qty=i) for i in range(1, 48)]  # total 47 (10 §1.5)


class Counter:
    def __init__(self) -> None:
        self.created: list[ItemOut] = []


def build_test_router(counter: Counter) -> APIRouter:
    router = APIRouter(prefix="/_test")

    @router.get("/ok", response_model=Envelope[ItemOut])
    def ok() -> Envelope[ItemOut]:
        return Envelope(data=ITEMS[0])

    @router.get("/ok-meta", response_model=Envelope[ItemOut])
    def ok_meta() -> Envelope[ItemOut]:
        return Envelope(data=ITEMS[0], meta={"generated_at": "2026-10-05T08:30:00+07:00"})

    @router.get("/api-error")
    def api_error() -> None:
        raise ApiError(ErrorCode.REVIEW_LOCKED, details={"locked_by": "u-1"})

    @router.get("/boom")
    def boom() -> None:
        raise RuntimeError("secret-internal-detail /srv/db password=hunter2")

    @router.post("/validate", response_model=Envelope[ItemOut])
    def validate(body: ItemIn) -> Envelope[ItemOut]:
        return Envelope(data=ItemOut(id=1, **body.model_dump()))

    @router.get("/items", response_model=Page[ItemOut])
    def items(params: Annotated[PageParams, Depends(get_page_params)]) -> Page[ItemOut]:
        rows = ITEMS[params.offset : params.offset + params.limit]
        return paginate(rows, params=params, total=len(ITEMS))

    @router.post("/items", status_code=201, response_model=Envelope[ItemOut])
    async def create_item(
        body: ItemIn, idem: Annotated[Idempotency, Depends(require_idempotency)]
    ) -> Response:
        def handler() -> Envelope[ItemOut]:
            item = ItemOut(id=len(counter.created) + 1, **body.model_dump())
            counter.created.append(item)
            return Envelope(data=item)

        return await idem.run(handler, status_code=201)

    @router.post("/items-optional", response_model=Envelope[ItemOut])
    async def create_item_optional(
        body: ItemIn, idem: Annotated[Idempotency, Depends(optional_idempotency)]
    ) -> Response:
        async def handler() -> Envelope[ItemOut]:
            item = ItemOut(id=len(counter.created) + 1, **body.model_dump())
            counter.created.append(item)
            return Envelope(data=item)

        return await idem.run(handler)

    @router.post("/items-fail")
    async def create_fail(
        body: ItemIn, idem: Annotated[Idempotency, Depends(require_idempotency)]
    ) -> Response:
        def handler() -> Envelope[ItemOut]:
            counter.created.append(ItemOut(id=0, **body.model_dump()))
            raise ApiError(ErrorCode.CONFLICT_STATE)

        return await idem.run(handler)

    return router


@pytest.fixture
def counter() -> Counter:
    return Counter()


@pytest.fixture
def store() -> InMemoryIdempotencyStore:
    return InMemoryIdempotencyStore()


@pytest.fixture
def test_app(counter: Counter, store: InMemoryIdempotencyStore) -> FastAPI:
    application = create_app()
    application.include_router(build_test_router(counter), prefix=API_PREFIX)
    application.dependency_overrides[get_idempotency_store] = lambda: store
    return application


@pytest.fixture
def client(test_app: FastAPI) -> Iterator[TestClient]:
    with TestClient(test_app) as c:
        yield c
