"""Supabase Database Service"""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from supabase import create_client, Client
from pydantic import BaseModel


class User(BaseModel):
    """User model"""
    id: str
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    language_code: str = "en"
    balance: float = 0
    referrer_id: Optional[str] = None
    personal_ref_percent: int = 20
    is_admin: bool = False
    is_banned: bool = False
    warnings_count: int = 0
    do_not_disturb: bool = False
    last_activity_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class Product(BaseModel):
    """Product model"""
    id: str
    name: str
    description: Optional[str] = None
    price: float
    type: str  # student, trial, shared, key
    status: str = "active"
    warranty_hours: int = 24
    instructions: Optional[str] = None
    terms: Optional[str] = None
    supplier_id: Optional[str] = None
    stock_count: int = 0  # Computed field
    fulfillment_time_hours: int = 48  # Time to fulfill on-demand order
    requires_prepayment: bool = False  # Whether prepayment is required
    prepayment_percent: int = 100  # Prepayment percentage (0-100)


class StockItem(BaseModel):
    """Stock item model"""
    id: str
    product_id: str
    content: str  # Login:Pass or invite link
    is_sold: bool = False
    expires_at: Optional[datetime] = None
    supplier_id: Optional[str] = None
    created_at: Optional[datetime] = None


class Order(BaseModel):
    """Order model"""
    id: str
    user_id: str
    product_id: str
    stock_item_id: Optional[str] = None
    amount: float
    original_price: Optional[float] = None
    discount_percent: int = 0
    status: str = "pending"
    payment_method: Optional[str] = None
    expires_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    refund_requested: bool = False
    created_at: Optional[datetime] = None


class Database:
    """Supabase database client with all operations"""
    
    def __init__(self):
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
        self.client: Client = create_client(url, key)
    
    # ==================== USER OPERATIONS ====================
    
    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID"""
        result = self.client.table("users").select("*").eq(
            "telegram_id", telegram_id
        ).execute()
        
        if result.data:
            return User(**result.data[0])
        return None
    
    async def create_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        language_code: str = "en",
        referrer_telegram_id: Optional[int] = None
    ) -> User:
        """Create new user with optional referrer"""
        referrer_id = None
        
        # Find referrer by telegram_id
        if referrer_telegram_id:
            referrer = await self.get_user_by_telegram_id(referrer_telegram_id)
            if referrer:
                referrer_id = referrer.id
        
        data = {
            "telegram_id": telegram_id,
            "username": username,
            "first_name": first_name,
            "language_code": language_code,
            "referrer_id": referrer_id,
            "last_activity_at": datetime.now(timezone.utc).isoformat()
        }
        
        result = self.client.table("users").insert(data).execute()
        return User(**result.data[0])
    
    async def update_user_language(self, telegram_id: int, language_code: str) -> None:
        """Update user's language code"""
        self.client.table("users").update({
            "language_code": language_code
        }).eq("telegram_id", telegram_id).execute()
    
    async def update_user_activity(self, telegram_id: int) -> None:
        """Update user's last activity timestamp"""
        self.client.table("users").update({
            "last_activity_at": datetime.now(timezone.utc).isoformat()
        }).eq("telegram_id", telegram_id).execute()
    
    async def update_user_balance(self, user_id: str, amount: float) -> None:
        """Add amount to user's balance (can be negative)"""
        user = self.client.table("users").select("balance").eq("id", user_id).execute()
        if user.data:
            new_balance = float(user.data[0]["balance"] or 0) + amount
            self.client.table("users").update({
                "balance": new_balance
            }).eq("id", user_id).execute()
    
    async def ban_user(self, telegram_id: int, ban: bool = True) -> None:
        """Ban or unban user"""
        self.client.table("users").update({
            "is_banned": ban
        }).eq("telegram_id", telegram_id).execute()
    
    async def add_warning(self, telegram_id: int) -> int:
        """Add warning to user, return new count"""
        user = await self.get_user_by_telegram_id(telegram_id)
        if user:
            new_count = user.warnings_count + 1
            # Auto-ban after 3 warnings
            update_data = {"warnings_count": new_count}
            if new_count >= 3:
                update_data["is_banned"] = True
            
            self.client.table("users").update(update_data).eq(
                "telegram_id", telegram_id
            ).execute()
            return new_count
        return 0
    
    # ==================== PRODUCT OPERATIONS ====================
    
    async def get_products(self, status: str = "active") -> List[Product]:
        """Get all active products with stock count"""
        result = self.client.table("products").select("*").eq(
            "status", status
        ).execute()
        
        products = []
        for p in result.data:
            # Count available stock
            stock = self.client.table("stock_items").select(
                "id", count="exact"
            ).eq("product_id", p["id"]).eq("is_sold", False).execute()
            
            p["stock_count"] = stock.count or 0
            products.append(Product(**p))
        
        return products
    
    async def get_product_by_id(self, product_id: str) -> Optional[Product]:
        """Get product by ID with stock count"""
        result = self.client.table("products").select("*").eq(
            "id", product_id
        ).execute()
        
        if result.data:
            p = result.data[0]
            # Count available stock
            stock = self.client.table("stock_items").select(
                "id", count="exact"
            ).eq("product_id", product_id).eq("is_sold", False).execute()
            
            p["stock_count"] = stock.count or 0
            return Product(**p)
        return None
    
    async def search_products(self, query: str) -> List[Product]:
        """Search products by name or description"""
        result = self.client.table("products").select("*").or_(
            f"name.ilike.%{query}%,description.ilike.%{query}%"
        ).eq("status", "active").execute()
        
        products = []
        for p in result.data:
            stock = self.client.table("stock_items").select(
                "id", count="exact"
            ).eq("product_id", p["id"]).eq("is_sold", False).execute()
            
            p["stock_count"] = stock.count or 0
            products.append(Product(**p))
        
        return products
    
    # ==================== STOCK OPERATIONS ====================
    
    async def get_available_stock_item(self, product_id: str) -> Optional[StockItem]:
        """Get first available stock item for product (oldest first)"""
        result = self.client.table("stock_items").select("*").eq(
            "product_id", product_id
        ).eq("is_sold", False).order("created_at").limit(1).execute()
        
        if result.data:
            return StockItem(**result.data[0])
        return None
    
    async def get_available_stock_count(self, product_id: str) -> int:
        """Get count of available stock items for product"""
        result = self.client.table("stock_items").select(
            "id", count="exact"
        ).eq("product_id", product_id).eq("is_sold", False).execute()
        
        return result.count or 0
    
    async def reserve_stock_item(self, stock_item_id: str) -> bool:
        """Mark stock item as sold (atomic operation)"""
        # Use RPC for atomic update with check
        result = self.client.table("stock_items").update({
            "is_sold": True
        }).eq("id", stock_item_id).eq("is_sold", False).execute()
        
        return len(result.data) > 0
    
    async def calculate_discount(self, stock_item: StockItem, product: Product) -> int:
        """Calculate discount based on stock item age"""
        if not stock_item.created_at:
            return 0
        
        # Calculate days in stock
        # Ensure both datetimes are timezone-aware
        now = datetime.now(timezone.utc)
        created_at = stock_item.created_at
        # If created_at is naive, make it aware (assume UTC)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        # If created_at is aware but different timezone, convert to UTC
        elif created_at.tzinfo != timezone.utc:
            created_at = created_at.astimezone(timezone.utc)
        
        days_in_stock = (now - created_at).days
        
        # Minimum 14 days for discount to apply
        if days_in_stock < 14:
            return 0
        
        # Get total duration (from expires_at or product warranty)
        if stock_item.expires_at:
            expires_at = stock_item.expires_at
            # Ensure expires_at is timezone-aware
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            elif expires_at.tzinfo != timezone.utc:
                expires_at = expires_at.astimezone(timezone.utc)
            total_days = (expires_at - created_at).days
        else:
            total_days = product.warranty_hours // 24 * 365  # Assume yearly if no expiry
        
        if total_days <= 0:
            return 0
        
        # Calculate discount: max 20%
        discount_coefficient = 0.5
        discount = min(20, int((days_in_stock / total_days) * discount_coefficient * 100))
        
        return discount
    
    # ==================== ORDER OPERATIONS ====================
    
    async def create_order(
        self,
        user_id: str,
        product_id: str,
        amount: float,
        original_price: Optional[float] = None,
        discount_percent: int = 0,
        payment_method: str = "aaio"
    ) -> Order:
        """Create new order"""
        data = {
            "user_id": user_id,
            "product_id": product_id,
            "amount": amount,
            "original_price": original_price or amount,
            "discount_percent": discount_percent,
            "status": "pending",
            "payment_method": payment_method
        }
        
        result = self.client.table("orders").insert(data).execute()
        return Order(**result.data[0])
    
    async def get_order_by_id(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        result = self.client.table("orders").select("*").eq("id", order_id).execute()
        if result.data:
            return Order(**result.data[0])
        return None
    
    async def update_order_status(
        self,
        order_id: str,
        status: str,
        stock_item_id: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ) -> None:
        """Update order status and optionally assign stock item"""
        data = {"status": status}
        
        if stock_item_id:
            data["stock_item_id"] = stock_item_id
        if expires_at:
            data["expires_at"] = expires_at.isoformat()
        if status == "completed":
            data["delivered_at"] = datetime.now(timezone.utc).isoformat()
        
        self.client.table("orders").update(data).eq("id", order_id).execute()
    
    async def get_user_orders(self, user_id: str, limit: int = 10) -> List[Order]:
        """Get user's orders"""
        result = self.client.table("orders").select("*").eq(
            "user_id", user_id
        ).order("created_at", desc=True).limit(limit).execute()
        
        return [Order(**o) for o in result.data]
    
    async def get_expiring_orders(self, days_before: int = 3) -> List[Order]:
        """Get orders expiring in N days"""
        target_date = datetime.now(timezone.utc) + timedelta(days=days_before)
        
        result = self.client.table("orders").select("*").eq(
            "status", "completed"
        ).lt("expires_at", target_date.isoformat()).gt(
            "expires_at", datetime.now(timezone.utc).isoformat()
        ).execute()
        
        return [Order(**o) for o in result.data]
    
    # ==================== CHAT HISTORY ====================
    
    async def save_chat_message(
        self,
        user_id: str,
        role: str,  # "user" or "assistant"
        message: str
    ) -> None:
        """Save chat message for conversation history"""
        self.client.table("chat_history").insert({
            "user_id": user_id,
            "role": role,
            "message": message
        }).execute()
    
    async def get_chat_history(self, user_id: str, limit: int = 20) -> List[Dict[str, str]]:
        """Get recent chat history for user"""
        result = self.client.table("chat_history").select("role,message").eq(
            "user_id", user_id
        ).order("timestamp", desc=True).limit(limit).execute()
        
        # Reverse to get chronological order
        return [{"role": m["role"], "content": m["message"]} for m in reversed(result.data)]
    
    # ==================== WAITLIST & WISHLIST ====================
    
    async def add_to_waitlist(self, user_id: str, product_name: str) -> None:
        """Add user to waitlist for a product"""
        import asyncio
        
        # Check if already in waitlist first (since there's no unique constraint)
        existing = await asyncio.to_thread(
            lambda: self.client.table("waitlist").select("id").eq(
                "user_id", user_id
            ).ilike("product_name", f"%{product_name}%").execute()
        )
        
        if existing.data:
            # Already in waitlist - this is not an error, just return
            return
        
        # Insert new entry
        await asyncio.to_thread(
            lambda: self.client.table("waitlist").insert({
                "user_id": user_id,
                "product_name": product_name
            }).execute()
        )
    
    async def add_to_wishlist(self, user_id: str, product_id: str) -> None:
        """Add product to user's wishlist"""
        self.client.table("wishlist").upsert({
            "user_id": user_id,
            "product_id": product_id
        }, on_conflict="user_id,product_id").execute()
    
    async def get_wishlist(self, user_id: str) -> List[Product]:
        """Get user's wishlist with product details"""
        result = self.client.table("wishlist").select(
            "product_id, products(*)"
        ).eq("user_id", user_id).execute()
        
        products = []
        for item in result.data:
            if item.get("products"):
                p = item["products"]
                p["stock_count"] = 0  # Will be computed if needed
                products.append(Product(**p))
        
        return products
    
    async def remove_from_wishlist(self, user_id: str, product_id: str) -> None:
        """Remove product from wishlist"""
        self.client.table("wishlist").delete().eq(
            "user_id", user_id
        ).eq("product_id", product_id).execute()
    
    # ==================== REVIEWS ====================
    
    async def create_review(
        self,
        user_id: str,
        order_id: str,
        product_id: str,
        rating: int,
        text: Optional[str] = None
    ) -> None:
        """Create product review"""
        self.client.table("reviews").insert({
            "user_id": user_id,
            "order_id": order_id,
            "product_id": product_id,
            "rating": rating,
            "text": text
        }).execute()
    
    async def get_product_reviews(self, product_id: str, limit: int = 5) -> List[Dict]:
        """Get recent reviews for product"""
        result = self.client.table("reviews").select(
            "rating,text,created_at,users(username,first_name)"
        ).eq("product_id", product_id).order(
            "created_at", desc=True
        ).limit(limit).execute()
        
        return result.data
    
    async def get_product_rating(self, product_id: str) -> Dict[str, Any]:
        """Get average rating and review count for product"""
        result = self.client.table("reviews").select(
            "rating"
        ).eq("product_id", product_id).execute()
        
        if not result.data:
            return {"average": 0, "count": 0}
        
        ratings = [r["rating"] for r in result.data]
        return {
            "average": round(sum(ratings) / len(ratings), 1),
            "count": len(ratings)
        }
    
    # ==================== PROMO CODES ====================
    
    async def validate_promo_code(self, code: str) -> Optional[Dict]:
        """Validate and get promo code details"""
        result = self.client.table("promo_codes").select("*").eq(
            "code", code.upper()
        ).eq("is_active", True).execute()
        
        if not result.data:
            return None
        
        promo = result.data[0]
        
        # Check expiration
        if promo.get("expires_at"):
            if datetime.fromisoformat(promo["expires_at"].replace("Z", "+00:00")) < datetime.now(timezone.utc):
                return None
        
        # Check usage limit
        if promo.get("usage_limit"):
            if promo["usage_count"] >= promo["usage_limit"]:
                return None
        
        return promo
    
    async def use_promo_code(self, code: str) -> None:
        """Increment promo code usage count"""
        self.client.rpc("increment_promo_usage", {"promo_code": code.upper()}).execute()
    
    # ==================== FAQ ====================
    
    async def get_faq(self, language_code: str = "en") -> List[Dict]:
        """Get FAQ entries for language"""
        result = self.client.table("faq").select("question,answer,category").eq(
            "language_code", language_code
        ).eq("is_active", True).order("order_index").execute()
        
        # Fallback to English if no results
        if not result.data and language_code != "en":
            result = self.client.table("faq").select("question,answer,category").eq(
                "language_code", "en"
            ).eq("is_active", True).order("order_index").execute()
        
        return result.data
    
    # ==================== ANALYTICS ====================
    
    async def log_event(
        self,
        user_id: Optional[str],
        event_type: str,
        metadata: Optional[Dict] = None
    ) -> None:
        """Log analytics event"""
        self.client.table("analytics_events").insert({
            "user_id": user_id,
            "event_type": event_type,
            "metadata": metadata or {}
        }).execute()
    
    # ==================== REFERRAL ====================
    
    async def process_referral_bonus(self, order: Order) -> None:
        """Process referral bonus for completed order"""
        # Get user with referrer
        user_result = self.client.table("users").select(
            "referrer_id,personal_ref_percent"
        ).eq("id", order.user_id).execute()
        
        if not user_result.data or not user_result.data[0].get("referrer_id"):
            return
        
        referrer_id = user_result.data[0]["referrer_id"]
        
        # Get referrer's commission rate
        referrer = self.client.table("users").select(
            "personal_ref_percent"
        ).eq("id", referrer_id).execute()
        
        if referrer.data:
            percent = referrer.data[0].get("personal_ref_percent", 20)
            bonus = order.amount * (percent / 100)
            await self.update_user_balance(referrer_id, bonus)


# Singleton instance
_db: Optional[Database] = None


def get_database() -> Database:
    """Get or create database instance"""
    global _db
    if _db is None:
        _db = Database()
    return _db

