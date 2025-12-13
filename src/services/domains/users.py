"""User domain service wrapping UserRepository."""
from typing import Optional

from src.services.models import User
from src.services.repositories import UserRepository


class UsersDomain:
    """User domain operations."""

    def __init__(self, repo: UserRepository):
        self.repo = repo

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        return await self.repo.get_by_telegram_id(telegram_id)

    async def create_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        language_code: str = "en",
        referrer_telegram_id: Optional[int] = None,
    ) -> User:
        referrer_id = None
        if referrer_telegram_id:
            referrer = await self.repo.get_by_telegram_id(referrer_telegram_id)
            if referrer:
                referrer_id = referrer.id
        return await self.repo.create(telegram_id, username, first_name, language_code, referrer_id)

    async def update_language(self, telegram_id: int, language_code: str) -> None:
        await self.repo.update_language(telegram_id, language_code)

    async def update_activity(self, telegram_id: int) -> None:
        await self.repo.update_activity(telegram_id)

    async def update_photo(self, telegram_id: int, photo_url: Optional[str]) -> None:
        await self.repo.update_photo(telegram_id, photo_url)

    async def update_balance(self, user_id: str, amount: float) -> None:
        await self.repo.update_balance(user_id, amount)

    async def ban(self, telegram_id: int, ban: bool = True) -> None:
        await self.repo.ban(telegram_id, ban)

    async def add_warning(self, telegram_id: int) -> int:
        return await self.repo.add_warning(telegram_id)

