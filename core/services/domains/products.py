"""Product domain service wrapping ProductRepository."""

from typing import Any

from core.services.models import Product
from core.services.repositories import ProductRepository


class ProductsDomain:
    """Product domain operations."""

    def __init__(self, repo: ProductRepository) -> None:
        self.repo = repo

    async def get_all(self, status: str = "active") -> list[Product]:
        return await self.repo.get_all(status)

    async def get_by_id(self, product_id: str) -> Product | None:
        return await self.repo.get_by_id(product_id)

    async def search(self, query: str) -> list[Product]:
        return await self.repo.search(query)

    async def get_rating(self, product_id: str) -> dict[str, Any]:
        return await self.repo.get_rating(product_id)
