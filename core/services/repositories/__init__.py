"""Repository Pattern for Database Operations.

Provides clean separation of concerns:
- UserRepository: User CRUD, auth, activity
- ProductRepository: Product catalog, search
- OrderRepository: Orders, payments
- StockRepository: Stock items, availability
- ChatRepository: Chat history, support tickets
"""

from .chat_repo import ChatRepository
from .order_repo import OrderRepository
from .product_repo import ProductRepository
from .stock_repo import StockRepository
from .user_repo import UserRepository

__all__ = [
    "ChatRepository",
    "OrderRepository",
    "ProductRepository",
    "StockRepository",
    "UserRepository",
]
