"""Chat domain service wrapping ChatRepository."""
from typing import List, Dict, Optional, Any

from core.services.repositories import ChatRepository


class ChatDomain:
    """Chat and support ticket operations."""

    def __init__(self, repo: ChatRepository):
        self.repo = repo

    async def save_message(self, user_id: str, role: str, message: str) -> None:
        await self.repo.save_message(user_id, role, message)

    async def get_history(self, user_id: str, limit: int = 20) -> List[Dict[str, str]]:
        return await self.repo.get_history(user_id, limit)

    async def create_ticket(
        self,
        user_id: str,
        subject: str,
        message: str,
        order_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await self.repo.create_ticket(user_id, subject, message, order_id)

    async def get_ticket(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        return await self.repo.get_ticket(ticket_id)

    async def get_user_tickets(self, user_id: str) -> List[Dict[str, Any]]:
        return await self.repo.get_user_tickets(user_id)

    async def update_ticket_status(self, ticket_id: str, status: str) -> None:
        await self.repo.update_ticket_status(ticket_id, status)

    async def add_ticket_message(self, ticket_id: str, sender: str, message: str) -> None:
        await self.repo.add_ticket_message(ticket_id, sender, message)

