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
# Service
# ============================================


class OffersService:
    """Automated offers for discount to PVNDORA migration."""

    # Thresholds
    LOYAL_PURCHASE_COUNT = 3
    INACTIVE_DAYS = 7

    def __init__(self, db_client):
        self.client = db_client
        self.promo_service = PromoCodeService(db_client)

    async def send_telegram_message(
        self, chat_id: int, text: str, use_discount_bot: bool = True
    ) -> bool:
        """Send a message via Telegram Bot API.

        Wrapper around consolidated telegram_messaging service.
        """
        from core.services.telegram_messaging import send_telegram_message as _send_msg

        token = DISCOUNT_BOT_TOKEN if use_discount_bot else TELEGRAM_TOKEN
        return await _send_msg(chat_id=chat_id, text=text, parse_mode="HTML", bot_token=token)

    # ==================== Offer: Loyal Customer (3+ purchases) ====================

    # Timing: Wait 2-3 days after 3rd purchase before sending loyal offer
    LOYAL_OFFER_DELAY_DAYS_MIN = 2
    LOYAL_OFFER_DELAY_DAYS_MAX = 5

    async def find_loyal_customers(self, limit: int = 50) -> list[OfferCandidate]:
        """Find discount users with 3+ orders who haven't received loyal offer.

        Only includes users whose 3rd purchase was 2-5 days ago (timing optimization).
        """
        try:
            # Timing window: 3rd purchase should be 2-5 days ago
            now = datetime.now(UTC)
            min_date = now - timedelta(days=self.LOYAL_OFFER_DELAY_DAYS_MAX)
            max_date = now - timedelta(days=self.LOYAL_OFFER_DELAY_DAYS_MIN)

            # Try RPC first (if exists)
            result = await self.client.rpc(
                "find_loyal_discount_customers",
                {"min_orders": self.LOYAL_PURCHASE_COUNT, "limit_count": limit},
            ).execute()

            if not result.data:
                # Fallback to direct query
                result = (
                    await self.client.table("users")
                    .select("id, telegram_id, language_code")
                    .eq("discount_tier_source", True)
                    .execute()
                )

                candidates = []
                for user in result.data or []:
                    # Get orders sorted by date to find 3rd purchase date
                    orders_result = (
                        await self.client.table("orders")
                        .select("id, delivered_at")
                        .eq("user_id", user["id"])
                        .eq("source_channel", "discount")
                        .eq("status", "delivered")
                        .order("delivered_at", desc=False)
                        .execute()
                    )

                    orders = orders_result.data or []
                    order_count = len(orders)

                    if order_count >= self.LOYAL_PURCHASE_COUNT:
                        # Check timing: 3rd purchase date
                        third_order = orders[self.LOYAL_PURCHASE_COUNT - 1]
                        third_order_date_str = third_order.get("delivered_at")
                        third_order_date = None

                        if third_order_date_str:
                            try:
                                third_order_date = datetime.fromisoformat(
                                    third_order_date_str.replace("Z", "+00:00")
                                )
                                # Only include if 3rd purchase was 2-5 days ago
                                if not (min_date <= third_order_date <= max_date):
                                    continue
                            except (ValueError, AttributeError):
                                continue  # Skip if date parsing fails
                        else:
                            continue  # Skip if no delivery date

                        # Check if already received loyal promo
                        existing = await self.promo_service.get_promo_by_trigger(
                            user["id"], PromoTriggers.LOYAL_3_PURCHASES
                        )

                        if not existing:
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

            # Filter RPC results by timing as well
            candidates = []
            for row in result.data:
                # Check timing if last_order_date is available
                last_date_str = row.get("last_order_date")
                if last_date_str:
                    try:
                        last_date = datetime.fromisoformat(last_date_str.replace("Z", "+00:00"))
                        if not (min_date <= last_date <= max_date):
                            continue
                    except (ValueError, AttributeError):
                        pass  # Include if can't parse

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

        except Exception:
            logger.exception("Failed to find loyal customers")
            return []

    async def send_loyal_offer(self, candidate: OfferCandidate) -> OfferResult:
        """Send loyal customer offer."""
        lang = candidate.language_code

        # Generate personal promo
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

        text = (
            (
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
            if lang == "ru"
            else (
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
        )

        success = await self.send_telegram_message(candidate.telegram_id, text)

        return OfferResult(
            success=success,
            telegram_id=candidate.telegram_id,
            trigger=candidate.trigger,
            promo_code=promo_code,
        )

    # ==================== Offer: Inactive Users (7+ days) ====================

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
                # Check if already received inactive promo recently
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
        lang = candidate.language_code

        # Generate personal promo
        promo_code = await self.promo_service.generate_personal_promo(
            user_id=candidate.user_id,
            telegram_id=candidate.telegram_id,
            trigger=PromoTriggers.INACTIVE_7_DAYS,
            discount_percent=30,  # Smaller discount for comeback
        )

        if not promo_code:
            return OfferResult(
                success=False,
                telegram_id=candidate.telegram_id,
                trigger=candidate.trigger,
                error="Failed to generate promo code",
            )

        text = (
            (
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
            if lang == "ru"
            else (
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
        )

        success = await self.send_telegram_message(candidate.telegram_id, text)

        return OfferResult(
            success=success,
            telegram_id=candidate.telegram_id,
            trigger=candidate.trigger,
            promo_code=promo_code,
        )

    # ==================== Batch Processing ====================

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

            # Rate limiting
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
