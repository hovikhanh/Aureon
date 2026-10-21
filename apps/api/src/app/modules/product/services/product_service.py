"""Public service interface of `product` — the only entry point for other modules."""

from sqlalchemy.ext.asyncio import AsyncSession


class ProductService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
