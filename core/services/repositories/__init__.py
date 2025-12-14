"""
Repository Pattern for Database Operations

Provides clean separation of concerns:
- UserRepository: User CRUD, auth, activity
- ProductRepository: Product catalog, search
- OrderRepository: Orders, payments
- StockRepository: Stock items, availability
- ChatRepository: Chat history, support tickets
"""
from .user_repo import UserRepository
from .product_repo import ProductRepository
from .order_repo import OrderRepository
from .stock_repo import StockRepository
from .chat_repo import ChatRepository

__all__ = [
    "UserRepository",
    "ProductRepository",
    "OrderRepository",
    "StockRepository",
    "ChatRepository",
]

