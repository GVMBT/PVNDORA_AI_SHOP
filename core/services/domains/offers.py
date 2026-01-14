"""Offers service for discount to PVNDORA migration.

Handles automated offer generation and sending.
All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""

import asyncio
import os
from datetime import UTC, datetime, timedelta

from pydantic import BaseModel

from core.logging import get_logger

from .promo import PromoCodeService, PromoTriggers

logger = get_logger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
DISCOUNT_BOT_TOKEN = os.environ.get("DISCOUNT_BOT_TOKEN", "")


# ============================================
# Models
# ============================================


class OfferCandidate(BaseModel):
    """User eligible for an offer."""

    user_id: str
    telegram_id: int
    language_code: str
    trigger: str
    order_count: int = 0
    last_order_date: datetime | None = None


class OfferResult(BaseModel):
    """Result of sending an offer."""

    success: bool
    telegram_id: int
    trigger: str
    promo_code: str | None = None
    error: str | None = None


# ============================================
# Helper Functions (reduce cognitive complexity)
# ============================================


def _parse_order_date(date_str: str | None) -> datetime | None:
    """Parse order date string to datetime."""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _is_date_in_range(date: datetime | None, min_date: datetime, max_date: datetime) -> bool:
    """Check if date is within the given range."""
    if not date:
        return False
    return min_date <= date <= max_date


async def _check_existing_promo(promo_service: PromoCodeService, user_id: str, trigger: str) -> bool:
    """Check if user already has a promo for this trigger. Returns True if exists."""
    existing = await promo_service.get_promo_by_trigger(user_id, trigger)
    return existing is not None


async def _get_user_orders(client, user_id: str) -> list:
    """Get user's delivered discount orders sorted by date."""
    orders_result = (
        await client.table("orders")
        .select("id, delivered_at")
        .eq("user_id", user_id)
        .eq("source_channel", "discount")
        .eq("status", "delivered")
        .order("delivered_at", desc=False)
        .execute()
    )
    return orders_result.data or []


def _build_loyal_message(candidate: OfferCandidate, promo_code: str, lang: str) -> str:
    """Build loyal customer offer message."""
    if lang == "ru":
        return (
            f"🎉 <b>Спасибо за доверие!</b>\n\n"
            f"Вы совершили {candidate.order_count} покупок — это круто!\n\n"
            f"В благодарность дарим вам <b>-50% на первую покупку</b> в PVNDORA:\n\n"
            f"🎁 <b>Промокод: {promo_code}</b>\n\n"
            f"В PVNDORA вас ждут:\n"
            f"• 🚀 Мгновенная доставка\n"
            f"• 🛡 Гарантии на все товары\n"
            f"• 💰 Партнерка 10/7/3%\n"
            f"• 🎧 Круглосуточная поддержка\n\n"
            f"👉 @pvndora_ai_bot"
        )
    return (
        f"🎉 <b>Thank you for your loyalty!</b>\n\n"
        f"You've made {candidate.order_count} purchases — awesome!\n\n"
        f"As a thank you, we're giving you <b>-50% off your first purchase</b> in PVNDORA:\n\n"
        f"🎁 <b>Promo code: {promo_code}</b>\n\n"
        f"In PVNDORA you get:\n"
        f"• 🚀 Instant delivery\n"
        f"• 🛡 Warranty on all products\n"
        f"• 💰 Affiliate 10/7/3%\n"
        f"• 🎧 24/7 support\n\n"
        f"👉 @pvndora_ai_bot"
    )


def _build_inactive_message(promo_code: str, lang: str) -> str:
    """Build inactive user offer message."""
    if lang == "ru":
        return (
            f"👋 <b>Мы скучаем!</b>\n\n"
            f"Давно не виделись. У нас много новых товаров:\n\n"
            f"• Новые AI-аккаунты\n"
            f"• Актуальные цены\n"
            f"• Быстрая доставка\n\n"
            f"Возвращайтесь с промокодом:\n"
            f"🎁 <b>{promo_code}</b> (-30%)\n\n"
            f"💡 Или попробуйте PVNDORA с мгновенной доставкой и гарантиями:\n"
            f"👉 @pvndora_ai_bot"
        )
    return (
        f"👋 <b>We miss you!</b>\n\n"
        f"It's been a while. We have lots of new products:\n\n"
        f"• New AI accounts\n"
        f"• Updated prices\n"
        f"• Fast delivery\n\n"
        f"Come back with promo code:\n"
        f"🎁 <b>{promo_code}</b> (-30%)\n\n"
        f"💡 Or try PVNDORA with instant delivery and warranties:\n"
        f"👉 @pvndora_ai_bot"
    )


# ============================================
# Service
# ============================================


class OffersService:
    """Automated offers for discount to PVNDORA migration."""

    # Thresholds
    LOYAL_PURCHASE_COUNT = 3
    INACTIVE_DAYS = 7

    # Timing: Wait 2-3 days after 3rd purchase before sending loyal offer
    LOYAL_OFFER_DELAY_DAYS_MIN = 2
    LOYAL_OFFER_DELAY_DAYS_MAX = 5

    def __init__(self, db_client):
        self.client = db_client
        self.promo_service = PromoCodeService(db_client)

    async def send_telegram_message(
        self, chat_id: int, text: str, use_discount_bot: bool = True
    ) -> bool:
        """Send a message via Telegram Bot API."""
        from core.services.telegram_messaging import send_telegram_message as _send_msg

        token = DISCOUNT_BOT_TOKEN if use_discount_bot else TELEGRAM_TOKEN
        return await _send_msg(chat_id=chat_id, text=text, parse_mode="HTML", bot_token=token)

    async def _find_loyal_via_rpc(self, limit: int, min_date: datetime, max_date: datetime) -> list[OfferCandidate]:
        """Find loyal customers via RPC."""
        result = await self.client.rpc(
            "find_loyal_discount_customers",
            {"min_orders": self.LOYAL_PURCHASE_COUNT, "limit_count": limit},
        ).execute()

        if not result.data:
            return []

        candidates = []
        for row in result.data:
            last_date = _parse_order_date(row.get("last_order_date"))
            if not _is_date_in_range(last_date, min_date, max_date):
                continue

            candidates.append(
                OfferCandidate(
                    user_id=row["user_id"],
                    telegram_id=row["telegram_id"],
                    language_code=row.get("language_code", "en"),
                    trigger=PromoTriggers.LOYAL_3_PURCHASES,
                    order_count=row.get("order_count", 3),
                )
            )
        return candidates

    async def _find_loyal_via_fallback(self, limit: int, min_date: datetime, max_date: datetime) -> list[OfferCandidate]:
        """Find loyal customers via direct query fallback."""
        result = (
            await self.client.table("users")
            .select("id, telegram_id, language_code")
            .eq("discount_tier_source", True)
            .execute()
        )

        candidates = []
        for user in result.data or []:
            orders = await _get_user_orders(self.client, user["id"])
            order_count = len(orders)

            if order_count < self.LOYAL_PURCHASE_COUNT:
                continue

            third_order = orders[self.LOYAL_PURCHASE_COUNT - 1]
            third_order_date = _parse_order_date(third_order.get("delivered_at"))

            if not _is_date_in_range(third_order_date, min_date, max_date):
                continue

            if await _check_existing_promo(self.promo_service, user["id"], PromoTriggers.LOYAL_3_PURCHASES):
                continue

            candidates.append(
                OfferCandidate(
                    user_id=user["id"],
                    telegram_id=user["telegram_id"],
                    language_code=user.get("language_code", "en"),
                    trigger=PromoTriggers.LOYAL_3_PURCHASES,
                    order_count=order_count,
                    last_order_date=third_order_date,
                )
            )

            if len(candidates) >= limit:
                break

        return candidates

    async def find_loyal_customers(self, limit: int = 50) -> list[OfferCandidate]:
        """Find discount users with 3+ orders who haven't received loyal offer."""
        try:
            now = datetime.now(UTC)
            min_date = now - timedelta(days=self.LOYAL_OFFER_DELAY_DAYS_MAX)
            max_date = now - timedelta(days=self.LOYAL_OFFER_DELAY_DAYS_MIN)

            # Try RPC first
            candidates = await self._find_loyal_via_rpc(limit, min_date, max_date)
            if candidates:
                return candidates

            # Fallback to direct query
            return await self._find_loyal_via_fallback(limit, min_date, max_date)

        except Exception:
            logger.exception("Failed to find loyal customers")
            return []

    async def send_loyal_offer(self, candidate: OfferCandidate) -> OfferResult:
        """Send loyal customer offer."""
        promo_code = await self.promo_service.generate_personal_promo(
            user_id=candidate.user_id,
            telegram_id=candidate.telegram_id,
            trigger=PromoTriggers.LOYAL_3_PURCHASES,
            discount_percent=50,
        )

        if not promo_code:
            return OfferResult(
                success=False,
                telegram_id=candidate.telegram_id,
                trigger=candidate.trigger,
                error="Failed to generate promo code",
            )

        text = _build_loyal_message(candidate, promo_code, candidate.language_code)
        success = await self.send_telegram_message(candidate.telegram_id, text)

        return OfferResult(
            success=success,
            telegram_id=candidate.telegram_id,
            trigger=candidate.trigger,
            promo_code=promo_code,
        )

    async def find_inactive_users(self, limit: int = 50) -> list[OfferCandidate]:
        """Find discount users inactive for 7+ days."""
        try:
            cutoff = datetime.now(UTC) - timedelta(days=self.INACTIVE_DAYS)

            result = (
                await self.client.table("users")
                .select("id, telegram_id, language_code, last_activity_at")
                .eq("discount_tier_source", True)
                .lt("last_activity_at", cutoff.isoformat())
                .limit(limit)
                .execute()
            )

            candidates = []
            for user in result.data or []:
                existing = await self.promo_service.get_promo_by_trigger(
                    user["id"], PromoTriggers.INACTIVE_7_DAYS
                )

                # Only send if no recent promo (within 30 days)
                if existing and existing.created_at:
                    promo_age = datetime.now(UTC) - existing.created_at
                    if promo_age < timedelta(days=30):
                        continue

                candidates.append(
                    OfferCandidate(
                        user_id=user["id"],
                        telegram_id=user["telegram_id"],
                        language_code=user.get("language_code", "en"),
                        trigger=PromoTriggers.INACTIVE_7_DAYS,
                    )
                )

            return candidates

        except Exception:
            logger.exception("Failed to find inactive users")
            return []

    async def send_inactive_offer(self, candidate: OfferCandidate) -> OfferResult:
        """Send offer to inactive user."""
        promo_code = await self.promo_service.generate_personal_promo(
            user_id=candidate.user_id,
            telegram_id=candidate.telegram_id,
            trigger=PromoTriggers.INACTIVE_7_DAYS,
            discount_percent=30,
        )

        if not promo_code:
            return OfferResult(
                success=False,
                telegram_id=candidate.telegram_id,
                trigger=candidate.trigger,
                error="Failed to generate promo code",
            )

        text = _build_inactive_message(promo_code, candidate.language_code)
        success = await self.send_telegram_message(candidate.telegram_id, text)

        return OfferResult(
            success=success,
            telegram_id=candidate.telegram_id,
            trigger=candidate.trigger,
            promo_code=promo_code,
        )

    async def process_all_offers(self) -> dict:
        """Process all offer types and return results."""
        results = {"loyal": {"sent": 0, "failed": 0}, "inactive": {"sent": 0, "failed": 0}}

        # Loyal customers
        loyal_candidates = await self.find_loyal_customers(limit=20)
        for candidate in loyal_candidates:
            result = await self.send_loyal_offer(candidate)
            if result.success:
                results["loyal"]["sent"] += 1
            else:
                results["loyal"]["failed"] += 1
            await asyncio.sleep(0.5)

        # Inactive users
        inactive_candidates = await self.find_inactive_users(limit=20)
        for candidate in inactive_candidates:
            result = await self.send_inactive_offer(candidate)
            if result.success:
                results["inactive"]["sent"] += 1
            else:
                results["inactive"]["failed"] += 1
            await asyncio.sleep(0.5)

        return results
