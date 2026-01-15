"""Referral Notifications.

Notifications for referral program events.
"""

from core.logging import get_logger

from .base import NotificationServiceBase, _msg, get_referral_settings, get_user_language

logger = get_logger(__name__)


class ReferralNotificationsMixin(NotificationServiceBase):
    """Mixin for referral-related notifications."""

    async def send_referral_unlock_notification(self, telegram_id: int) -> None:
        """Send notification when referral program is unlocked after first purchase."""
        lang = await get_user_language(telegram_id)
        settings = await get_referral_settings()
        l1 = settings["level1_percent"]
        l2 = settings["level2_percent"]
        l3 = settings["level3_percent"]
        t2 = settings["level2_threshold"]
        t3 = settings["level3_threshold"]

        message = _msg(
            lang,
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            f"   🔗 <b>ПАРТНЁРКА АКТИВИРОВАНА</b>\n"
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"Добро пожаловать в сеть PVNDORA.\n"
            f"Теперь вы получаете бонусы с покупок друзей.\n\n"
            f"<b>▸ УРОВЕНЬ 1</b> — активен\n"
            f"   └ <b>{l1}%</b> с покупок рефералов\n\n"
            f"<b>▸ УРОВЕНЬ 2</b> — оборот ${t2}+\n"
            f"   └ +{l2}% со 2-й линии\n\n"
            f"<b>▸ УРОВЕНЬ 3</b> — оборот ${t3}+\n"
            f"   └ +{l3}% с 3-й линии\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📋 <i>Ссылка и статистика — в профиле</i>",
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            f"   🔗 <b>AFFILIATE ACTIVATED</b>\n"
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"Welcome to the PVNDORA network.\n"
            f"You now earn bonuses from friends' purchases.\n\n"
            f"<b>▸ LEVEL 1</b> — active\n"
            f"   └ <b>{l1}%</b> from referrals\n\n"
            f"<b>▸ LEVEL 2</b> — turnover ${t2}+\n"
            f"   └ +{l2}% from tier 2\n\n"
            f"<b>▸ LEVEL 3</b> — turnover ${t3}+\n"
            f"   └ +{l3}% from tier 3\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📋 <i>Link & stats — in your profile</i>",
        )

        try:
            from core.services.telegram_messaging import send_telegram_message

            await send_telegram_message(chat_id=telegram_id, text=message, parse_mode="HTML")
        except Exception:
            logger.exception("Failed to send referral unlock notification")

    async def send_referral_level_up_notification(self, telegram_id: int, new_level: int) -> None:
        """Send notification when user's referral level increases."""
        lang = await get_user_language(telegram_id)
        settings = await get_referral_settings()
        l1 = settings["level1_percent"]
        l2 = settings["level2_percent"]
        l3 = settings["level3_percent"]
        t3 = settings["level3_threshold"]

        if new_level == 2:
            message = _msg(
                lang,
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
                f"    📈 <b>УРОВЕНЬ ПОВЫШЕН</b>\n"
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
                f"Вы достигли <b>Уровня 2</b>.\n"
                f"Теперь активна 2-я линия рефералов.\n\n"
                f"<b>▸ ЛИНИЯ 1:</b> {l1}%\n"
                f"<b>▸ ЛИНИЯ 2:</b> +{l2}% ← новое\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"До Уровня 3: оборот ${t3}",
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
                f"    📈 <b>LEVEL UP</b>\n"
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
                f"You've reached <b>Level 2</b>.\n"
                f"Tier 2 referrals now active.\n\n"
                f"<b>▸ TIER 1:</b> {l1}%\n"
                f"<b>▸ TIER 2:</b> +{l2}% ← new\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"To Level 3: ${t3} turnover",
            )
        elif new_level == 3:
            message = _msg(
                lang,
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
                f"    🏆 <b>ПРОТОКОЛ ЗАВЕРШЁН</b>\n"
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
                f"Поздравляем, оперативник!\n"
                f"<b>Уровень 3</b> — предел сети.\n"
                f"Все линии доступа активны.\n\n"
                f"<b>▸ ЛИНИЯ 1:</b> {l1}%\n"
                f"<b>▸ ЛИНИЯ 2:</b> {l2}%\n"
                f"<b>▸ ЛИНИЯ 3:</b> +{l3}% ← новое\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"💎 <i>Все протоколы разблокированы</i>",
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
                f"    🏆 <b>PROTOCOL COMPLETE</b>\n"
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
                f"Congratulations, operative!\n"
                f"<b>Level 3</b> — network limit.\n"
                f"All access lines active.\n\n"
                f"<b>▸ TIER 1:</b> {l1}%\n"
                f"<b>▸ TIER 2:</b> {l2}%\n"
                f"<b>▸ TIER 3:</b> +{l3}% ← new\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"💎 <i>All protocols unlocked</i>",
            )
        else:
            return

        try:
            from core.services.telegram_messaging import send_telegram_message

            await send_telegram_message(chat_id=telegram_id, text=message, parse_mode="HTML")
        except Exception:
            logger.exception("Failed to send referral level up notification")

    async def send_referral_bonus_notification(
        self,
        telegram_id: int,
        bonus_amount: float,
        referral_name: str,
        purchase_amount: float,
        line: int = 1,
    ) -> None:
        """Notify referrer about bonus from referral purchase."""
        lang = await get_user_language(telegram_id)

        line_info_ru = f" • линия {line}" if line > 1 else ""
        line_info_en = f" • tier {line}" if line > 1 else ""

        message = _msg(
            lang,
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            f"     💸 <b>БОНУС ПОЛУЧЕН</b>\n"
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"Ваш реферал <b>{referral_name}</b>{line_info_ru}\n"
            f"совершил покупку.\n\n"
            f"◈ <b>Сумма покупки:</b> ${purchase_amount:.2f}\n"
            f"◈ <b>Ваш бонус:</b> +${bonus_amount:.2f}\n\n"
            f"<i>Зачислено на баланс</i> ✓",
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            f"     💸 <b>BONUS RECEIVED</b>\n"
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"Your referral <b>{referral_name}</b>{line_info_en}\n"
            f"made a purchase.\n\n"
            f"◈ <b>Purchase:</b> ${purchase_amount:.2f}\n"
            f"◈ <b>Your bonus:</b> +${bonus_amount:.2f}\n\n"
            f"<i>Credited to balance</i> ✓",
        )

        try:
            from core.services.telegram_messaging import send_telegram_message

            await send_telegram_message(chat_id=telegram_id, text=message, parse_mode="HTML")
            logger.info(f"Sent referral bonus notification to {telegram_id}")
        except Exception:
            logger.exception(f"Failed to send referral bonus notification to {telegram_id}")

    async def send_new_referral_notification(
        self, telegram_id: int, referral_name: str, line: int = 1,
    ) -> None:
        """Notify referrer about new referral joining."""
        lang = await get_user_language(telegram_id)

        line_info_ru = f" • линия {line}" if line > 1 else ""
        line_info_en = f" • tier {line}" if line > 1 else ""

        message = _msg(
            lang,
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            f"     👤 <b>НОВЫЙ РЕФЕРАЛ</b>\n"
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"<b>{referral_name}</b>{line_info_ru}\n"
            f"присоединился к вашей сети.\n\n"
            f"<i>Бонусы с его покупок — автоматически</i> ✓",
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            f"     👤 <b>NEW REFERRAL</b>\n"
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"<b>{referral_name}</b>{line_info_en}\n"
            f"joined your network.\n\n"
            f"<i>Bonuses from their purchases — automatic</i> ✓",
        )

        try:
            from core.services.telegram_messaging import send_telegram_message

            await send_telegram_message(chat_id=telegram_id, text=message, parse_mode="HTML")
            logger.info(f"Sent new referral notification to {telegram_id}")
        except Exception:
            logger.exception(f"Failed to send new referral notification to {telegram_id}")
