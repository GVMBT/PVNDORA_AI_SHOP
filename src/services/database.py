"""
Supabase Database Service

Provides Database class with all operations via Repository pattern.
Maintains backward compatibility while delegating to specialized repositories.

Usage:
    from src.services.database import get_database, User, Product, Order
    db = get_database()
    user = await db.get_user_by_telegram_id(123)
"""
import os
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from supabase import create_client, Client

# Re-export models for backward compatibility
from src.services.models import User, Product, StockItem, Order

# Import repositories
from src.services.repositories import (
    UserRepository,
    ProductRepository,
    OrderRepository,
    StockRepository,
    ChatRepository,
)


class Database:
    """
    Supabase database client with all operations.
    
    Uses Repository pattern internally but exposes flat API for backward compatibility.
    """
    
    def __init__(self):
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
        
        self.client: Client = create_client(url, key)
        
        # Initialize repositories
        self._users = UserRepository(self.client)
        self._products = ProductRepository(self.client)
        self._orders = OrderRepository(self.client)
        self._stock = StockRepository(self.client)
        self._chat = ChatRepository(self.client)
    
    # ==================== USER OPERATIONS (delegated) ====================
    
    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        return await self._users.get_by_telegram_id(telegram_id)
    
    async def create_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        language_code: str = "en",
        referrer_telegram_id: Optional[int] = None
    ) -> User:
        referrer_id = None
        if referrer_telegram_id:
            referrer = await self._users.get_by_telegram_id(referrer_telegram_id)
            if referrer:
                referrer_id = referrer.id
        return await self._users.create(telegram_id, username, first_name, language_code, referrer_id)
    
    async def update_user_language(self, telegram_id: int, language_code: str) -> None:
        await self._users.update_language(telegram_id, language_code)
    
    async def update_user_activity(self, telegram_id: int) -> None:
        await self._users.update_activity(telegram_id)
    
    async def update_user_balance(self, user_id: str, amount: float) -> None:
        await self._users.update_balance(user_id, amount)
    
    async def ban_user(self, telegram_id: int, ban: bool = True) -> None:
        await self._users.ban(telegram_id, ban)
    
    async def add_warning(self, telegram_id: int) -> int:
        return await self._users.add_warning(telegram_id)
    
    # ==================== PRODUCT OPERATIONS (delegated) ====================
    
    async def get_products(self, status: str = "active") -> List[Product]:
        return await self._products.get_all(status)
    
    async def get_product_by_id(self, product_id: str) -> Optional[Product]:
        return await self._products.get_by_id(product_id)
    
    async def search_products(self, query: str) -> List[Product]:
        return await self._products.search(query)
    
    async def get_product_rating(self, product_id: str) -> Dict[str, Any]:
        return await self._products.get_rating(product_id)
    
    # ==================== STOCK OPERATIONS (delegated) ====================
    
    async def get_available_stock_item(self, product_id: str) -> Optional[StockItem]:
        return await self._stock.get_available(product_id)
    
    async def get_available_stock_count(self, product_id: str) -> int:
        return await self._stock.get_available_count(product_id)
    
    async def reserve_stock_item(self, stock_item_id: str) -> bool:
        return await self._stock.reserve(stock_item_id)
    
    async def calculate_discount(self, stock_item: StockItem, product: Product) -> int:
        return await self._stock.calculate_discount(stock_item, product)
    
    # ==================== ORDER OPERATIONS (delegated) ====================
    
    async def create_order(
        self,
        user_id: str,
        product_id: str,
        amount: float,
        original_price: Optional[float] = None,
        discount_percent: int = 0,
        payment_method: str = "1plat",
        user_telegram_id: Optional[int] = None
    ) -> Order:
        return await self._orders.create(user_id, product_id, amount, original_price, discount_percent, payment_method, user_telegram_id)
    
    async def create_order_with_availability_check(
        self,
        product_id: str,
        user_telegram_id: int
    ) -> Dict[str, Any]:
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
        import asyncio
        
        def _call_rpc():
            result = self.client.rpc(
                "create_order_with_availability_check",
                {
                    "p_product_id": product_id,
                    "p_user_telegram_id": user_telegram_id
                }
            ).execute()
            
            if not result.data:
                raise ValueError("Failed to create order")
            
            return result.data[0]
        
        # Execute sync RPC call in thread pool
        return await asyncio.to_thread(_call_rpc)
    
    async def get_order_by_id(self, order_id: str) -> Optional[Order]:
        return await self._orders.get_by_id(order_id)
    
    async def update_order_status(
        self,
        order_id: str,
        status: str,
        stock_item_id: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ) -> None:
        await self._orders.update_status(order_id, status, stock_item_id, expires_at)
    
    async def get_user_orders(self, user_id: str, limit: int = 10) -> List[Order]:
        return await self._orders.get_by_user(user_id, limit)
    
    async def get_expiring_orders(self, days_before: int = 3) -> List[Order]:
        return await self._orders.get_expiring(days_before)
    
    # ==================== CHAT HISTORY (delegated) ====================
    
    async def save_chat_message(self, user_id: str, role: str, message: str) -> None:
        await self._chat.save_message(user_id, role, message)
    
    async def get_chat_history(self, user_id: str, limit: int = 20) -> List[Dict[str, str]]:
        return await self._chat.get_history(user_id, limit)
    
    # ==================== WAITLIST & WISHLIST (kept in main class) ====================
    
    async def add_to_waitlist(self, user_id: str, product_name: str) -> None:
        """Add user to waitlist for a product."""
        import asyncio
        existing = await asyncio.to_thread(
            lambda: self.client.table("waitlist").select("id").eq(
                "user_id", user_id
            ).ilike("product_name", f"%{product_name}%").execute()
        )
        if existing.data:
            return
        await asyncio.to_thread(
            lambda: self.client.table("waitlist").insert({
                "user_id": user_id, "product_name": product_name
            }).execute()
        )
    
    async def add_to_wishlist(self, user_id: str, product_id: str) -> None:
        """Add product to user's wishlist."""
        self.client.table("wishlist").upsert({
            "user_id": user_id, "product_id": product_id
        }, on_conflict="user_id,product_id").execute()
    
    async def get_wishlist(self, user_id: str) -> List[Product]:
        """Get user's wishlist with product details."""
        result = self.client.table("wishlist").select("product_id, products(*)").eq("user_id", user_id).execute()
        products = []
        for item in result.data:
            if item.get("products"):
                p = item["products"]
                p["stock_count"] = 0
                products.append(Product(**p))
        return products
    
    async def remove_from_wishlist(self, user_id: str, product_id: str) -> None:
        """Remove product from wishlist."""
        self.client.table("wishlist").delete().eq("user_id", user_id).eq("product_id", product_id).execute()
    
    # ==================== REVIEWS ====================
    
    async def create_review(
        self, user_id: str, order_id: str, product_id: str, rating: int, text: Optional[str] = None
    ) -> None:
        """Create product review."""
        self.client.table("reviews").insert({
            "user_id": user_id, "order_id": order_id, "product_id": product_id,
            "rating": rating, "text": text
        }).execute()
    
    async def get_product_reviews(self, product_id: str, limit: int = 5) -> List[Dict]:
        """Get recent reviews for product."""
        result = self.client.table("reviews").select(
            "rating,text,created_at,users(username,first_name)"
        ).eq("product_id", product_id).order("created_at", desc=True).limit(limit).execute()
        return result.data
    
    # ==================== PROMO CODES ====================
    
    async def validate_promo_code(self, code: str) -> Optional[Dict]:
        """Validate and get promo code details."""
        result = self.client.table("promo_codes").select("*").eq(
            "code", code.upper()
        ).eq("is_active", True).execute()
        
        if not result.data:
            return None
        
        promo = result.data[0]
        if promo.get("expires_at"):
            if datetime.fromisoformat(promo["expires_at"].replace("Z", "+00:00")) < datetime.now(timezone.utc):
                return None
        if promo.get("usage_limit") and promo["usage_count"] >= promo["usage_limit"]:
            return None
        
        return promo
    
    async def use_promo_code(self, code: str) -> None:
        """Increment promo code usage count."""
        self.client.rpc("increment_promo_usage", {"promo_code": code.upper()}).execute()
    
    # ==================== FAQ ====================
    
    async def get_faq(self, language_code: str = "en") -> List[Dict]:
        """Get FAQ entries for language."""
        result = self.client.table("faq").select("id,question,answer,category").eq(
            "language_code", language_code
        ).eq("is_active", True).order("order_index").execute()
        
        if not result.data and language_code != "en":
            result = self.client.table("faq").select("id,question,answer,category").eq(
                "language_code", "en"
            ).eq("is_active", True).order("order_index").execute()
        
        return result.data
    
    # ==================== ANALYTICS ====================
    
    async def log_event(self, user_id: Optional[str], event_type: str, metadata: Optional[Dict] = None) -> None:
        """Log analytics event."""
        self.client.table("analytics_events").insert({
            "user_id": user_id, "event_type": event_type, "metadata": metadata or {}
        }).execute()
    
    # ==================== REFERRAL ====================
    
    REFERRAL_LEVELS = [
        {"level": 1, "percent": 20},
        {"level": 2, "percent": 10},
        {"level": 3, "percent": 5},
    ]
    
    async def process_referral_bonus(self, order: Order) -> None:
        """Process 3-level referral bonus for completed order."""
        current_user_id = order.user_id
        bonuses_awarded = []
        
        for level_config in self.REFERRAL_LEVELS:
            level = level_config["level"]
            percent = level_config["percent"]
            
            user_result = self.client.table("users").select("referrer_id").eq("id", current_user_id).execute()
            if not user_result.data or not user_result.data[0].get("referrer_id"):
                break
            
            referrer_id = user_result.data[0]["referrer_id"]
            if referrer_id == order.user_id:
                print(f"WARNING: Self-referral loop detected at L{level}")
                break
            
            bonus = round(order.amount * (percent / 100), 2)
            await self.update_user_balance(referrer_id, bonus)
            
            self.client.table("referral_bonuses").insert({
                "user_id": referrer_id,
                "from_user_id": str(order.user_id),
                "order_id": str(order.id),
                "level": level,
                "percent": percent,
                "amount": bonus
            }).execute()
            
            self.client.rpc("increment_referral_earnings", {"p_user_id": referrer_id, "p_amount": bonus}).execute()
            
            bonuses_awarded.append({"level": level, "referrer_id": referrer_id, "bonus": bonus})
            print(f"Referral L{level}: {percent}% = {bonus}₽ to user {referrer_id}")
            
            current_user_id = referrer_id
        
        if bonuses_awarded:
            print(f"Total referral bonuses: {sum(b['bonus'] for b in bonuses_awarded)}₽")


# Singleton instance
_db: Optional[Database] = None


def get_database() -> Database:
    """Get or create database instance."""
    global _db
    if _db is None:
        _db = Database()
    return _db
