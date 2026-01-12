"""Stock domain service wrapping StockRepository."""

from core.services.models import Product, StockItem
from core.services.repositories import StockRepository


class StockDomain:
    """Stock domain operations."""

    def __init__(self, repo: StockRepository):
        self.repo = repo

    async def get_available(self, product_id: str) -> StockItem | None:
        return await self.repo.get_available(product_id)

    async def get_available_count(self, product_id: str) -> int:
        return await self.repo.get_available_count(product_id)

    async def reserve(self, stock_item_id: str) -> bool:
        return await self.repo.reserve(stock_item_id)

    async def calculate_discount(self, stock_item: StockItem, product: Product) -> int:
        return await self.repo.calculate_discount(stock_item, product)
