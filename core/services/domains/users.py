"""User domain service wrapping UserRepository."""

from core.logging import get_logger
from core.services.models import User
from core.services.repositories import UserRepository

logger = get_logger(__name__)


class UsersDomain:
    """User domain operations."""

    def __init__(self, repo: UserRepository) -> None:
        self.repo = repo

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        return await self.repo.get_by_telegram_id(telegram_id)

    async def create_user(
        self,
        telegram_id: int,
        username: str | None = None,
        first_name: str | None = None,
        language_code: str = "en",
        referrer_telegram_id: int | None = None,
    ) -> User:
        referrer_id = None
        referrer = None
        if referrer_telegram_id:
            referrer = await self.repo.get_by_telegram_id(referrer_telegram_id)
            if referrer:
                referrer_id = referrer.id

        new_user = await self.repo.create(
            telegram_id, username, first_name, language_code, referrer_id,
        )

        # Notify referrer about new referral (best-effort)
        if referrer and referrer.telegram_id:
            try:
                from core.routers.deps import get_notification_service

                notification_service = get_notification_service()
                referral_name = username or first_name or f"ID:{telegram_id}"
                await notification_service.send_new_referral_notification(
                    telegram_id=referrer.telegram_id, referral_name=referral_name, line=1,
                )
            except Exception as e:
                logger.warning(f"Failed to send new referral notification: {e}")

        return new_user

    async def update_language(self, telegram_id: int, language_code: str) -> None:
        await self.repo.update_language(telegram_id, language_code)

    async def update_activity(self, telegram_id: int) -> None:
        await self.repo.update_activity(telegram_id)

    async def update_photo(self, telegram_id: int, photo_url: str | None) -> None:
        await self.repo.update_photo(telegram_id, photo_url)

    async def update_balance(self, user_id: str, amount: float) -> None:
        await self.repo.update_balance(user_id, amount)

    async def ban(self, telegram_id: int, ban: bool = True) -> None:
        await self.repo.ban(telegram_id, ban)

    async def add_warning(self, telegram_id: int) -> int:
        return await self.repo.add_warning(telegram_id)

    async def update_preferences(
        self,
        telegram_id: int,
        preferred_currency: str | None = None,
        interface_language: str | None = None,
    ) -> None:
        """Update user preferences for currency and interface language."""
        await self.repo.update_preferences(telegram_id, preferred_currency, interface_language)
