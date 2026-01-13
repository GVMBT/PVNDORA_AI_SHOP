"""User Repository - User CRUD operations.

All methods use async/await with supabase-py v2.
"""

from datetime import UTC, datetime

from core.logging import get_logger
from core.services.models import User
from core.services.money import to_decimal, to_float

from .base import BaseRepository

logger = get_logger(__name__)


class UserRepository(BaseRepository):
    """User database operations."""

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """Get user by Telegram ID."""
        result = (
            await self.client.table("users").select("*").eq("telegram_id", telegram_id).execute()
        )
        return User(**result.data[0]) if result.data else None

    async def get_by_id(self, user_id: str) -> User | None:
        """Get user by internal ID."""
        result = await self.client.table("users").select("*").eq("id", user_id).execute()
        return User(**result.data[0]) if result.data else None

    async def create(
        self,
        telegram_id: int,
        username: str | None = None,
        first_name: str | None = None,
        language_code: str = "en",
        referrer_id: str | None = None,
    ) -> User:
        """Create new user with balance_currency determined by language_code."""
        from core.services.currency import CurrencyService

        # Determine balance_currency based on language_code (ru/be/kk → RUB, others → USD)
        currency_service = CurrencyService()
        balance_currency = currency_service.get_balance_currency(language_code)

        data = {
            "telegram_id": telegram_id,
            "username": username,
            "first_name": first_name,
            "language_code": language_code,
            "referrer_id": referrer_id,
            "balance_currency": balance_currency,  # Set based on language_code
            "last_activity_at": datetime.now(UTC).isoformat(),
        }
        result = await self.client.table("users").insert(data).execute()
        return User(**result.data[0])

    async def update_language(self, telegram_id: int, language_code: str) -> None:
        """Update user's language."""
        await (
            self.client.table("users")
            .update({"language_code": language_code})
            .eq("telegram_id", telegram_id)
            .execute()
        )

    async def update_activity(self, telegram_id: int) -> None:
        """Update last activity timestamp."""
        await (
            self.client.table("users")
            .update({"last_activity_at": datetime.now(UTC).isoformat()})
            .eq("telegram_id", telegram_id)
            .execute()
        )

    async def update_photo(self, telegram_id: int, photo_url: str | None) -> None:
        """Update user's photo URL."""
        if photo_url:
            await (
                self.client.table("users")
                .update({"photo_url": photo_url})
                .eq("telegram_id", telegram_id)
                .execute()
            )

    async def update_balance(self, user_id: str, amount: float) -> None:
        """Add amount to balance (can be negative)."""
        user = await self.client.table("users").select("balance").eq("id", user_id).execute()
        if user.data:
            new_balance = to_float(to_decimal(user.data[0]["balance"] or 0) + to_decimal(amount))
            await (
                self.client.table("users")
                .update({"balance": new_balance})
                .eq("id", user_id)
                .execute()
            )

    async def ban(self, telegram_id: int, ban: bool = True) -> None:
        """Ban or unban user."""
        await (
            self.client.table("users")
            .update({"is_banned": ban})
            .eq("telegram_id", telegram_id)
            .execute()
        )

    async def add_warning(self, telegram_id: int) -> int:
        """Add warning, return new count. Auto-ban at 3."""
        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            return 0

        new_count = user.warnings_count + 1
        update_data = {"warnings_count": new_count}
        if new_count >= 3:
            update_data["is_banned"] = True

        await (
            self.client.table("users").update(update_data).eq("telegram_id", telegram_id).execute()
        )
        return new_count

    async def update_preferences(
        self,
        telegram_id: int,
        preferred_currency: str | None = None,
        interface_language: str | None = None,
    ) -> None:
        """Update user preferences for currency and interface language."""
        update_data = {}
        if preferred_currency is not None:
            update_data["preferred_currency"] = (
                preferred_currency.upper() if preferred_currency else None
            )
        if interface_language is not None:
            update_data["interface_language"] = (
                interface_language.lower() if interface_language else None
            )

        if update_data:
            # Don't log telegram_id (user-controlled data) - just log success
            logger.info("Updating user preferences: %s", update_data)
            try:
                await (
                    self.client.table("users")
                    .update(update_data)
                    .eq("telegram_id", telegram_id)
                    .execute()
                )
                # Don't log telegram_id (user-controlled data) - just log success
                logger.info("Successfully updated user preferences")
            except Exception as e:
                # Don't log full telegram_id (user-controlled), just log error type
                logger.error(
                    "Failed to update preferences for user: %s",
                    type(e).__name__,
                    exc_info=True,
                )
                raise

    async def get_admins(self):
        """Get all admin users."""
        result = await self.client.table("users").select("*").eq("is_admin", True).execute()
        return [User(**u) for u in result.data]
