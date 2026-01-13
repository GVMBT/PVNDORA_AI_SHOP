"""
Supabase Database Service

Provides Database class with all operations via Repository pattern.
Maintains backward compatibility while delegating to specialized repositories.

Usage:
    from core.services.database import get_database, User, Product, Order

    # In async context (after init_database() called at startup):
    db = get_database()
    user = await db.get_user_by_telegram_id(123)

    # At FastAPI startup (lifespan):
    await init_database()
"""

import asyncio
import os
from datetime import UTC, datetime
from typing import Any, Optional

from supabase._async.client import AsyncClient
from supabase._async.client import create_client as acreate_client

from core.logging import get_logger

logger = get_logger(__name__)

# Domain services
from core.services.domains import ChatDomain, OrdersDomain, ProductsDomain, StockDomain, UsersDomain
from core.services.domains.support import SupportService

# Re-export models for backward compatibility
from core.services.models import Order, Product, StockItem, User

# Import repositories
from core.services.repositories import (
    ChatRepository,
    OrderRepository,
    ProductRepository,
    StockRepository,
    UserRepository,
)


class Database:
    """
    Supabase database client with all operations.

    Uses Repository pattern internally but exposes flat API for backward compatibility.

    IMPORTANT: This class uses async Supabase client (AsyncClient).
    Must be initialized via async factory method `create()` or `init_database()`.
    """

    def __init__(self, client: AsyncClient):
        """Private constructor. Use Database.create() or init_database() instead."""
        self.client = client

        # Initialize repositories with async client
        self._users_repo = UserRepository(self.client)
        self._products_repo = ProductRepository(self.client)
        self._orders_repo = OrderRepository(self.client)
        self._stock_repo = StockRepository(self.client)
        self._chat_repo = ChatRepository(self.client)

        # Domains
        self.users_domain = UsersDomain(self._users_repo)
        self.products_domain = ProductsDomain(self._products_repo)
        self.stock_domain = StockDomain(self._stock_repo)
        self.orders_domain = OrdersDomain(self._orders_repo, self.client)
        self.chat_domain = ChatDomain(self._chat_repo)
        self.support_domain = SupportService(self)  # Support service uses Database instance

    @classmethod
    async def create(cls) -> "Database":
        """Async factory method to create Database instance.

        Creates async Supabase client and initializes all repositories.
        """
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")

        client = await acreate_client(url, key)
        return cls(client)

    # ==================== USER OPERATIONS (delegated) ====================

    async def get_user_by_telegram_id(self, telegram_id: int) -> User | None:
        return await self.users_domain.get_by_telegram_id(telegram_id)

    async def create_user(
        self,
        telegram_id: int,
        username: str | None = None,
        first_name: str | None = None,
        language_code: str = "en",
        referrer_telegram_id: int | None = None,
    ) -> User:
        return await self.users_domain.create_user(
            telegram_id,
            username,
            first_name,
            language_code,
            referrer_telegram_id,
        )

    async def update_user_language(self, telegram_id: int, language_code: str) -> None:
        await self.users_domain.update_language(telegram_id, language_code)

    async def update_user_preferences(
        self,
        telegram_id: int,
        preferred_currency: str | None = None,
        interface_language: str | None = None,
    ) -> None:
        """Update user preferences for currency and interface language."""
        await self.users_domain.update_preferences(
            telegram_id, preferred_currency, interface_language
        )

    async def update_user_activity(self, telegram_id: int) -> None:
        await self.users_domain.update_activity(telegram_id)

    async def update_user_photo(self, telegram_id: int, photo_url: str | None) -> None:
        await self.users_domain.update_photo(telegram_id, photo_url)

    async def update_user_balance(self, user_id: str, amount: float) -> None:
        await self.users_domain.update_balance(user_id, amount)

    async def ban_user(self, telegram_id: int, ban: bool = True) -> None:
        await self.users_domain.ban(telegram_id, ban)

    async def add_warning(self, telegram_id: int) -> int:
        return await self.users_domain.add_warning(telegram_id)

    # ==================== PRODUCT OPERATIONS (delegated) ====================

    async def get_products(self, status: str = "active") -> list[Product]:
        return await self.products_domain.get_all(status)

    async def get_product_by_id(self, product_id: str) -> Product | None:
        return await self.products_domain.get_by_id(product_id)

    async def search_products(self, query: str) -> list[Product]:
        return await self.products_domain.search(query)

    async def get_product_rating(self, product_id: str) -> dict[str, Any]:
        return await self.products_domain.get_rating(product_id)

    # ==================== STOCK OPERATIONS (delegated) ====================

    async def get_available_stock_item(self, product_id: str) -> StockItem | None:
        return await self.stock_domain.get_available(product_id)

    async def get_available_stock_count(self, product_id: str) -> int:
        return await self.stock_domain.get_available_count(product_id)

    async def reserve_stock_item(self, stock_item_id: str) -> bool:
        return await self.stock_domain.reserve(stock_item_id)

    def calculate_discount(self, stock_item: StockItem, product: Product) -> int:
        return self.stock_domain.calculate_discount(stock_item, product)

    # ==================== ORDER OPERATIONS (delegated) ====================

    async def create_order(
        self,
        user_id: str,
        amount: float,
        original_price: float | None = None,
        discount_percent: int = 0,
        payment_method: str = "card",
        payment_gateway: str = "crystalpay",
        user_telegram_id: int | None = None,
        expires_at: datetime | None = None,
        payment_url: str | None = None,
        # New currency snapshot fields
        fiat_amount: float | None = None,
        fiat_currency: str | None = None,
        exchange_rate_snapshot: float | None = None,
    ) -> Order:
        """Create new order.

        Note: product_id removed - products are stored in order_items table.

        Args:
            fiat_amount: Amount in user's currency (what they see/pay)
            fiat_currency: User's currency code (RUB, USD, etc.)
            exchange_rate_snapshot: Exchange rate at order creation (1 USD = X fiat)
        """
        return await self.orders_domain.create(
            user_id=user_id,
            amount=amount,
            original_price=original_price,
            discount_percent=discount_percent,
            payment_method=payment_method,
            payment_gateway=payment_gateway,
            user_telegram_id=user_telegram_id,
            expires_at=expires_at,
            payment_url=payment_url,
            fiat_amount=fiat_amount,
            fiat_currency=fiat_currency,
            exchange_rate_snapshot=exchange_rate_snapshot,
        )

    async def create_order_with_availability_check(
        self, product_id: str, user_telegram_id: int
    ) -> dict[str, Any]:
        """
        Create order with automatic availability check.

        Uses PostgreSQL RPC function that:
        - If product is in stock → creates instant order (reserves stock item)
        - If product is not in stock → creates prepaid order automatically

        Args:
            product_id: Product UUID
            user_telegram_id: Telegram user ID

        Returns:
            Dict with order_id, order_type, status, stock_item_id, amount, fulfillment_deadline
        """
        return await self.orders_domain.create_with_availability_check(product_id, user_telegram_id)

    async def get_order_by_id(self, order_id: str) -> Order | None:
        return await self.orders_domain.get_by_id(order_id)

    async def update_order_status(
        self, order_id: str, status: str, expires_at: datetime | None = None
    ) -> None:
        """Update order status.

        Note: stock_item_id removed - stock items are linked via order_items table.
        """
        await self.orders_domain.update_status(order_id, status, expires_at)

    async def get_user_orders(
        self,
        user_id: str,
        limit: int = 10,
        offset: int = 0,
        source_channel: str | None = None,
        exclude_source_channel: str | None = None,
    ) -> list[Order]:
        return await self.orders_domain.get_by_user(
            user_id,
            limit,
            offset,
            source_channel=source_channel,
            exclude_source_channel=exclude_source_channel,
        )

    async def get_expiring_orders(self, days_before: int = 3) -> list[Order]:
        return await self.orders_domain.get_expiring(days_before)

    # ==================== ORDER ITEMS ====================
    async def create_order_items(self, items: list[dict]) -> list[dict]:
        """Batch insert order_items."""
        return await self.orders_domain.create_order_items(items)

    async def get_order_items_by_order(self, order_id: str) -> list[dict]:
        return await self.orders_domain.get_order_items_by_order(order_id)

    async def get_order_items_by_orders(self, order_ids: list[str]) -> list[dict]:
        return await self.orders_domain.get_order_items_by_orders(order_ids)

    # ==================== CHAT HISTORY (delegated) ====================

    async def save_chat_message(self, user_id: str, role: str, message: str) -> None:
        await self.chat_domain.save_message(user_id, role, message)

    async def get_chat_history(self, user_id: str, limit: int = 20) -> list[dict[str, str]]:
        return await self.chat_domain.get_history(user_id, limit)

    async def create_ticket(
        self, user_id: str, subject: str, message: str, order_id: str | None = None
    ) -> dict[str, Any]:
        return await self.chat_domain.create_ticket(user_id, subject, message, order_id)

    async def get_ticket(self, ticket_id: str) -> dict[str, Any] | None:
        return await self.chat_domain.get_ticket(ticket_id)

    async def get_user_tickets(self, user_id: str) -> list[dict[str, Any]]:
        return await self.chat_domain.get_user_tickets(user_id)

    async def update_ticket_status(self, ticket_id: str, status: str) -> None:
        await self.chat_domain.update_ticket_status(ticket_id, status)

    async def add_ticket_message(self, ticket_id: str, sender: str, message: str) -> None:
        await self.chat_domain.add_ticket_message(ticket_id, sender, message)

    # ==================== WAITLIST & WISHLIST (kept in main class) ====================

    async def add_to_waitlist(self, user_id: str, product_name: str) -> None:
        """Add user to waitlist for a product."""
        existing = (
            await self.client.table("waitlist")
            .select("id")
            .eq("user_id", user_id)
            .ilike("product_name", f"%{product_name}%")
            .execute()
        )
        if existing.data:
            return
        await (
            self.client.table("waitlist")
            .insert({"user_id": user_id, "product_name": product_name})
            .execute()
        )

    async def add_to_wishlist(self, user_id: str, product_id: str) -> None:
        """Add product to user's wishlist."""
        await (
            self.client.table("wishlist")
            .upsert(
                {"user_id": user_id, "product_id": product_id}, on_conflict="user_id,product_id"
            )
            .execute()
        )

    async def get_wishlist(self, user_id: str) -> list[Product]:
        """Get user's wishlist with product details."""
        result = (
            await self.client.table("wishlist")
            .select("product_id, products(*)")
            .eq("user_id", user_id)
            .execute()
        )
        products = []
        for item in result.data:
            if item.get("products"):
                p = item["products"]
                p["stock_count"] = 0
                products.append(Product(**p))
        return products

    async def remove_from_wishlist(self, user_id: str, product_id: str) -> None:
        """Remove product from wishlist."""
        await (
            self.client.table("wishlist")
            .delete()
            .eq("user_id", user_id)
            .eq("product_id", product_id)
            .execute()
        )

    # ==================== REVIEWS ====================

    async def create_review(
        self, user_id: str, order_id: str, product_id: str, rating: int, text: str | None = None
    ) -> None:
        """Create product review."""
        await (
            self.client.table("reviews")
            .insert(
                {
                    "user_id": user_id,
                    "order_id": order_id,
                    "product_id": product_id,
                    "rating": rating,
                    "text": text,
                }
            )
            .execute()
        )

    async def get_product_reviews(self, product_id: str, limit: int = 5) -> list[dict]:
        """Get recent reviews for product."""
        result = (
            await self.client.table("reviews")
            .select("rating,text,created_at,users(username,first_name)")
            .eq("product_id", product_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data

    # ==================== PROMO CODES ====================

    async def validate_promo_code(self, code: str) -> dict | None:
        """Validate and get promo code details.

        Returns promo code with product_id:
        - product_id IS NULL: applies to entire cart
        - product_id IS NOT NULL: applies only to that specific product
        """
        result = (
            await self.client.table("promo_codes")
            .select("*")
            .eq("code", code.upper())
            .eq("is_active", True)
            .execute()
        )

        if not result.data:
            return None

        promo = result.data[0]
        if promo.get("expires_at") and datetime.fromisoformat(
            promo["expires_at"].replace("Z", "+00:00")
        ) < datetime.now(UTC):
            return None
        if promo.get("usage_limit") and promo["usage_count"] >= promo["usage_limit"]:
            return None

        # product_id is included in the result (can be NULL for cart-wide promos)
        return promo

    async def use_promo_code(self, code: str) -> None:
        """Increment promo code usage count."""
        await self.client.rpc("increment_promo_usage", {"p_code": code.upper()}).execute()

    # ==================== FAQ ====================

    async def get_faq(self, language_code: str = "en") -> list[dict]:
        """Get FAQ entries for language."""
        result = (
            await self.client.table("faq")
            .select("id,question,answer,category")
            .eq("language_code", language_code)
            .eq("is_active", True)
            .order("order_index")
            .execute()
        )

        if not result.data and language_code != "en":
            result = (
                await self.client.table("faq")
                .select("id,question,answer,category")
                .eq("language_code", "en")
                .eq("is_active", True)
                .order("order_index")
                .execute()
            )

        return result.data

    # ==================== ANALYTICS ====================

    async def log_event(
        self, user_id: str | None, event_type: str, metadata: dict | None = None
    ) -> None:
        """Log analytics event."""
        await (
            self.client.table("analytics_events")
            .insert({"user_id": user_id, "event_type": event_type, "metadata": metadata or {}})
            .execute()
        )

    # ==================== REFERRAL ====================

    # NOTE: These are fallback values. Actual percentages loaded from referral_settings table.
    # Primary referral processing is via RPC process_referral_bonus in workers.py
    REFERRAL_LEVELS = [
        {"level": 1, "percent": 10},
        {"level": 2, "percent": 7},
        {"level": 3, "percent": 3},
    ]

    async def process_referral_bonus(self, order: Order) -> None:
        """Process 3-level referral bonus for completed order."""
        current_user_id = order.user_id
        bonuses_awarded = []

        for level_config in self.REFERRAL_LEVELS:
            level = level_config["level"]
            percent = level_config["percent"]

            user_result = (
                await self.client.table("users")
                .select("referrer_id")
                .eq("id", current_user_id)
                .execute()
            )
            if not user_result.data or not user_result.data[0].get("referrer_id"):
                break

            referrer_id = user_result.data[0]["referrer_id"]
            if referrer_id == order.user_id:
                logger.warning(f"Self-referral loop detected at L{level}")
                break

            bonus = round(order.amount * (percent / 100), 2)
            await self.update_user_balance(referrer_id, bonus)

            await (
                self.client.table("referral_bonuses")
                .insert(
                    {
                        "user_id": referrer_id,
                        "from_user_id": str(order.user_id),
                        "order_id": str(order.id),
                        "level": level,
                        "percent": percent,
                        "amount": bonus,
                    }
                )
                .execute()
            )

            await self.client.rpc(
                "increment_referral_earnings", {"p_user_id": referrer_id, "p_amount": bonus}
            ).execute()

            bonuses_awarded.append({"level": level, "referrer_id": referrer_id, "bonus": bonus})
            logger.info(f"Referral L{level}: {percent}% = {bonus}₽ to user {referrer_id}")

            current_user_id = referrer_id

        if bonuses_awarded:
            logger.info(f"Total referral bonuses: {sum(b['bonus'] for b in bonuses_awarded)}₽")


# Singleton instance (initialized lazily or at startup via init_database())
_db: Database | None = None
_db_lock: Optional["asyncio.Lock"] = None  # Lazy lock for thread-safe init


def _get_lock() -> "asyncio.Lock":
    """Get or create async lock for thread-safe initialization."""
    global _db_lock
    if _db_lock is None:
        import asyncio

        _db_lock = asyncio.Lock()
    return _db_lock


async def init_database() -> Database:
    """Initialize async database singleton.

    Can be called at FastAPI startup (lifespan) or lazily on first use.
    Thread-safe via async lock.

    Returns:
        Database instance (also cached as singleton)
    """
    global _db
    if _db is not None:
        return _db

    async with _get_lock():
        # Double-check after acquiring lock
        if _db is None:
            logger.info("Initializing async Supabase client...")
            _db = await Database.create()
            logger.info("Async Supabase client initialized successfully")
    return _db


async def close_database() -> None:
    """Close database connections.

    Should be called at FastAPI shutdown (lifespan).
    """
    global _db
    if _db is not None:
        try:
            # Close the async client session
            await _db.client.auth.sign_out()
        except Exception as e:
            logger.warning(f"Error closing Supabase client: {e}")
        _db = None
        logger.info("Supabase client closed")


async def get_database_async() -> Database:
    """Get database instance with lazy async initialization.

    Use this in cron jobs and standalone serverless functions
    where lifespan is not available.

    Returns:
        Database instance
    """
    if _db is None:
        return await init_database()
    return _db


def get_database() -> Database:
    """Get database instance (sync accessor).

    IMPORTANT: Either:
    1. Call init_database() at startup (main app lifespan), OR
    2. Use get_database_async() in cron/worker contexts

    For cron jobs, prefer get_database_async() for lazy initialization.

    Raises:
        RuntimeError: If database not initialized

    Returns:
        Database instance
    """
    if _db is None:
        raise RuntimeError(
            "Database not initialized. Use 'await get_database_async()' for lazy init, "
            "or call 'await init_database()' at startup."
        )
    return _db


def is_database_initialized() -> bool:
    """Check if database singleton is initialized."""
    return _db is not None
