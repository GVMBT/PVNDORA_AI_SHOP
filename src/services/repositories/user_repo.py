"""User Repository - User CRUD operations."""
from datetime import datetime, timezone
from typing import Optional
from .base import BaseRepository
from src.services.models import User
from src.services.money import to_decimal, to_float


class UserRepository(BaseRepository):
    """User database operations."""
    
    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID."""
        result = self.client.table("users").select("*").eq("telegram_id", telegram_id).execute()
        return User(**result.data[0]) if result.data else None
    
    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by internal ID."""
        result = self.client.table("users").select("*").eq("id", user_id).execute()
        return User(**result.data[0]) if result.data else None
    
    async def create(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        language_code: str = "en",
        referrer_id: Optional[str] = None
    ) -> User:
        """Create new user."""
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
    
    async def update_language(self, telegram_id: int, language_code: str) -> None:
        """Update user's language."""
        self.client.table("users").update({"language_code": language_code}).eq("telegram_id", telegram_id).execute()
    
    async def update_activity(self, telegram_id: int) -> None:
        """Update last activity timestamp."""
        self.client.table("users").update({
            "last_activity_at": datetime.now(timezone.utc).isoformat()
        }).eq("telegram_id", telegram_id).execute()
    
    async def update_photo(self, telegram_id: int, photo_url: Optional[str]) -> None:
        """Update user's photo URL."""
        if photo_url:
            self.client.table("users").update({
                "photo_url": photo_url
            }).eq("telegram_id", telegram_id).execute()
    
    async def update_balance(self, user_id: str, amount: float) -> None:
        """Add amount to balance (can be negative)."""
        user = self.client.table("users").select("balance").eq("id", user_id).execute()
        if user.data:
            new_balance = to_float(to_decimal(user.data[0]["balance"] or 0) + to_decimal(amount))
            self.client.table("users").update({"balance": new_balance}).eq("id", user_id).execute()
    
    async def ban(self, telegram_id: int, ban: bool = True) -> None:
        """Ban or unban user."""
        self.client.table("users").update({"is_banned": ban}).eq("telegram_id", telegram_id).execute()
    
    async def add_warning(self, telegram_id: int) -> int:
        """Add warning, return new count. Auto-ban at 3."""
        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            return 0
        
        new_count = user.warnings_count + 1
        update_data = {"warnings_count": new_count}
        if new_count >= 3:
            update_data["is_banned"] = True
        
        self.client.table("users").update(update_data).eq("telegram_id", telegram_id).execute()
        return new_count
    
    async def update_preferences(self, telegram_id: int, preferred_currency: Optional[str] = None, interface_language: Optional[str] = None) -> None:
        """Update user preferences for currency and interface language."""
        update_data = {}
        if preferred_currency is not None:
            update_data["preferred_currency"] = preferred_currency.upper() if preferred_currency else None
        if interface_language is not None:
            update_data["interface_language"] = interface_language.lower() if interface_language else None
        
        if update_data:
            self.client.table("users").update(update_data).eq("telegram_id", telegram_id).execute()
    
    async def get_admins(self):
        """Get all admin users."""
        result = self.client.table("users").select("*").eq("is_admin", True).execute()
        return [User(**u) for u in result.data]

