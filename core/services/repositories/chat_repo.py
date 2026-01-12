"""Chat Repository - Chat history and support tickets."""

from typing import Any

from .base import BaseRepository


class ChatRepository(BaseRepository):
    """Chat history and support operations."""

    async def save_message(self, user_id: str, role: str, message: str) -> None:
        """Save chat message."""
        await self.client.table("chat_history").insert(
            {"user_id": user_id, "role": role, "message": message}
        ).execute()

    async def get_history(self, user_id: str, limit: int = 20) -> list[dict[str, str]]:
        """Get recent chat history (chronological order)."""
        result = (
            await self.client.table("chat_history")
            .select("role,message")
            .eq("user_id", user_id)
            .order("timestamp", desc=True)
            .limit(limit)
            .execute()
        )

        return [{"role": m["role"], "content": m["message"]} for m in reversed(result.data)]

    async def create_ticket(
        self, user_id: str, subject: str, message: str, order_id: str | None = None
    ) -> dict[str, Any]:
        """Create support ticket."""
        result = (
            await self.client.table("support_tickets")
            .insert(
                {
                    "user_id": user_id,
                    "subject": subject,
                    "initial_message": message,
                    "order_id": order_id,
                    "status": "open",
                }
            )
            .execute()
        )
        return result.data[0] if result.data else {}

    async def get_ticket(self, ticket_id: str) -> dict[str, Any] | None:
        """Get support ticket by ID."""
        result = (
            await self.client.table("support_tickets").select("*").eq("id", ticket_id).execute()
        )
        return result.data[0] if result.data else None

    async def get_user_tickets(self, user_id: str) -> list[dict[str, Any]]:
        """Get user's support tickets."""
        result = (
            await self.client.table("support_tickets")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data

    async def update_ticket_status(self, ticket_id: str, status: str) -> None:
        """Update ticket status."""
        await self.client.table("support_tickets").update({"status": status}).eq(
            "id", ticket_id
        ).execute()

    async def add_ticket_message(self, ticket_id: str, sender: str, message: str) -> None:
        """Add message to ticket."""
        await self.client.table("ticket_messages").insert(
            {"ticket_id": ticket_id, "sender": sender, "message": message}
        ).execute()
