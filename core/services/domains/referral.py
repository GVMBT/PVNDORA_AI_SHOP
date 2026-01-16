"""Referral Domain Service.

Handles referral system operations.
All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""

from dataclasses import dataclass
from typing import Any

from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ReferralLevel:
    """Referral level info."""

    level: int
    count: int
    percent: int


@dataclass
class ReferralInfo:
    """User's referral information."""

    success: bool
    referral_link: str | None = None
    total_referrals: int = 0
    balance: float = 0.0
    levels: dict[int, ReferralLevel] | None = None
    error: str | None = None


class ReferralService:
    """Referral domain service.

    Provides clean interface for referral operations.
    """

    # Referral commission percentages by level (fallback, actual values from DB)
    # NOTE: These are fallback values. Actual percentages loaded from referral_settings table.
    LEVEL_PERCENTS = {1: 10, 2: 7, 3: 3}
    BOT_USERNAME = "pvndora_ai_bot"

    def __init__(self, db: Any) -> None:
        self.db = db

    async def get_info(self, user_id: str) -> ReferralInfo:
        """Get user's referral information.

        Args:
            user_id: User database ID

        Returns:
            ReferralInfo with link and stats

        """
        try:
            # Get user data
            user_result = (
                await self.db.client.table("users")
                .select("telegram_id,balance,personal_ref_percent")
                .eq("id", user_id)
                .execute()
            )

            if not user_result.data:
                return ReferralInfo(success=False, error="User not found")

            user = user_result.data[0]
            telegram_id = user["telegram_id"]

            # Count referrals by level
            levels = await self._count_referral_levels(user_id)

            total = sum(level.count for level in levels.values())

            return ReferralInfo(
                success=True,
                referral_link=f"https://t.me/{self.BOT_USERNAME}?start=ref_{telegram_id}",
                total_referrals=total,
                balance=user.get("balance", 0.0),
                levels=levels,
            )
        except Exception as e:
            logger.error(f"Failed to get referral info: {e}", exc_info=True)
            return ReferralInfo(success=False, error=str(e))

    async def _count_referral_levels(self, user_id: str) -> dict[int, ReferralLevel]:
        """Count referrals at each level.

        Returns dict with levels 1, 2, 3.
        """
        levels = {
            1: ReferralLevel(level=1, count=0, percent=self.LEVEL_PERCENTS[1]),
            2: ReferralLevel(level=2, count=0, percent=self.LEVEL_PERCENTS[2]),
            3: ReferralLevel(level=3, count=0, percent=self.LEVEL_PERCENTS[3]),
        }

        # Level 1 - direct referrals
        level1_result = (
            await self.db.client.table("users")
            .select("id", count="exact")
            .eq("referrer_id", user_id)
            .execute()
        )
        levels[1].count = level1_result.count or 0

        if levels[1].count == 0:
            return levels

        # Get level 1 IDs for deeper traversal
        level1_ids = [r["id"] for r in (level1_result.data or [])]

        if not level1_ids:
            return levels

        # Level 2 - referrals of referrals (BATCH query to avoid N+1)
        l2_result = (
            await self.db.client.table("users")
            .select("id, referrer_id", count="exact")
            .in_("referrer_id", level1_ids)
            .execute()
        )
        levels[2].count = l2_result.count or 0

        # Level 3 - referrals of level 2 (BATCH query to avoid N+1)
        if l2_result.data:
            l2_ids = [l2["id"] for l2 in l2_result.data]
            l3_result = (
                await self.db.client.table("users")
                .select("id", count="exact")
                .in_("referrer_id", l2_ids)
                .execute()
            )
            levels[3].count = l3_result.count or 0

        return levels

    async def get_referral_earnings(self, user_id: str) -> dict[str, Any]:
        """Get user's referral earnings history.

        Args:
            user_id: User database ID

        Returns:
            Earnings summary

        """
        try:
            result = (
                await self.db.client.table("referral_earnings")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(50)
                .execute()
            )

            total_earned = sum(e.get("amount", 0) for e in result.data or [])

            return {
                "success": True,
                "total_earned": total_earned,
                "transactions": result.data or [],
            }
        except Exception as e:
            logger.error(f"Failed to get referral earnings: {e}", exc_info=True)
            return {"success": False, "total_earned": 0, "transactions": []}
