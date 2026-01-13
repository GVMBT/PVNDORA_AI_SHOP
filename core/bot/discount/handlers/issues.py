"""Discount bot issue/problem handlers.
All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.types import CallbackQuery

from core.logging import get_logger
from core.services.database import User, get_database
from core.services.domains import InsuranceService, PromoCodeService, PromoTriggers

from ..keyboards import (
    get_issue_result_keyboard,
    get_issue_types_keyboard,
)

logger = get_logger(__name__)

router = Router(name="discount_issues")


# Helper functions (extracted to reduce cognitive complexity)
def _format_replacement_id(rep_id: str | None) -> str:
    """Format replacement ID for display."""
    return rep_id[:8] if rep_id else "N/A"


def _get_replacement_approved_message(rep_id: str | None, is_ru: bool) -> str:
    """Get message for approved replacement."""
    rep_id_short = _format_replacement_id(rep_id)
    if is_ru:
        return (
            "✅ <b>Замена одобрена!</b>\n\n"
            f"Новый товар будет доставлен в течение 1-4 часов.\n\n"
            f"ID замены: #{rep_id_short}"
        )
    return (
        "✅ <b>Replacement approved!</b>\n\n"
        f"Your new item will be delivered within 1-4 hours.\n\n"
        f"Replacement ID: #{rep_id_short}"
    )


def _get_replacement_pending_message(rep_id: str | None, is_ru: bool) -> str:
    """Get message for pending replacement."""
    rep_id_short = _format_replacement_id(rep_id)
    if is_ru:
        return (
            "⏳ <b>Запрос на замену создан</b>\n\n"
            f"Наша команда рассмотрит его в ближайшее время.\n\n"
            f"ID замены: #{rep_id_short}"
        )
    return (
        "⏳ <b>Replacement request created</b>\n\n"
        f"Our team will review it shortly.\n\n"
        f"Replacement ID: #{rep_id_short}"
    )


async def get_order_item_with_insurance(db, order_short_id: str) -> dict | None:
    """Get order item with insurance info."""
    try:
        # Get order
        order_result = (
            await db.client.table("orders")
            .select("id, user_id")
            .ilike("id", f"{order_short_id}%")
            .limit(1)
            .execute()
        )

        if not order_result.data:
            return None

        order = order_result.data[0]

        # Get order items with insurance
        items_result = (
            await db.client.table("order_items")
            .select("id, insurance_id, insurance_expires_at, product_id, stock_item_id")
            .eq("order_id", order["id"])
            .limit(1)
            .execute()
        )

        if not items_result.data:
            return None

        item = items_result.data[0]
        item["order_id"] = order["id"]
        item["user_id"] = order["user_id"]

        return item

    except Exception:
        logger.exception("Failed to get order item")
        return None


@router.callback_query(F.data.startswith("discount:issue:"))
async def cb_issue_start(callback: CallbackQuery, db_user: User):
    """Start issue reporting flow."""
    lang = db_user.language_code

    order_short_id = callback.data.split(":")[2]

    text = (
        ("⚠️ <b>Проблема с аккаунтом</b>\n\nВыберите тип проблемы:")
        if lang == "ru"
        else ("⚠️ <b>Account Problem</b>\n\nSelect issue type:")
    )

    await callback.message.edit_text(
        text, reply_markup=get_issue_types_keyboard(order_short_id, lang), parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data.startswith("discount:issue_type:"))
async def cb_issue_type_selected(callback: CallbackQuery, db_user: User):
    """Process issue type and check insurance."""
    lang = db_user.language_code
    db = get_database()

    parts = callback.data.split(":")
    order_short_id = parts[2]
    issue_type = parts[3]

    # Get order item
    order_item = await get_order_item_with_insurance(db, order_short_id)

    if not order_item:
        await callback.answer(
            "Заказ не найден" if lang == "ru" else "Order not found", show_alert=True
        )
        return

    # Issue type to reason mapping
    reason_map = {
        "login_failed": "Cannot login to account",
        "banned": "Account was banned",
        "wrong_product": "Received wrong product",
        "other": "Other issue",
    }
    reason = reason_map.get(issue_type, issue_type)

    # Check insurance
    insurance_service = InsuranceService(db.client)
    promo_service = PromoCodeService(db.client)

    has_insurance = order_item.get("insurance_id") is not None
    can_replace = False
    promo_code = None

    if has_insurance:
        # Check if insurance is valid and replacements available
        is_valid, ins_id, remaining = await insurance_service.check_insurance_valid(
            order_item["id"]
        )
        can_replace = is_valid and remaining > 0

        if can_replace:
            # Request replacement
            result = await insurance_service.request_replacement(
                order_item_id=order_item["id"], telegram_id=db_user.telegram_id, reason=reason
            )

            if result.success:
                is_approved = result.status == "auto_approved"
                text = (
                    _get_replacement_approved_message(result.replacement_id, lang == "ru")
                    if is_approved
                    else _get_replacement_pending_message(result.replacement_id, lang == "ru")
                )

                await callback.message.edit_text(
                    text,
                    reply_markup=get_issue_result_keyboard(True, False, None, lang),
                    parse_mode=ParseMode.HTML,
                )
                await callback.answer()
                return
            # Replacement failed (limit reached, blocked, etc.)
            can_replace = False

            # Check if it's a limit issue -> offer PVNDORA
            if result.status == "rejected" and "limit" in result.message.lower():
                # Generate promo for limit reached
                promo_code = await promo_service.generate_personal_promo(
                    user_id=order_item["user_id"],
                    telegram_id=db_user.telegram_id,
                    trigger=PromoTriggers.REPLACEMENT_LIMIT,
                    discount_percent=50,
                )

    # No insurance or can't replace
    if not has_insurance:
        # Generate promo for no insurance
        promo_code = await promo_service.generate_personal_promo(
            user_id=order_item["user_id"],
            telegram_id=db_user.telegram_id,
            trigger=PromoTriggers.ISSUE_NO_INSURANCE,
            discount_percent=50,
        )

    if has_insurance and not can_replace:
        # Insurance expired or limit reached
        existing_promo = await promo_service.get_promo_by_trigger(
            order_item["user_id"], PromoTriggers.INSURANCE_EXPIRED
        )

        if not existing_promo:
            promo_code = await promo_service.generate_personal_promo(
                user_id=order_item["user_id"],
                telegram_id=db_user.telegram_id,
                trigger=PromoTriggers.INSURANCE_EXPIRED,
                discount_percent=50,
            )
        else:
            promo_code = existing_promo.code

    # Show result
    if has_insurance and not can_replace:
        text = (
            (
                "⚠️ <b>Страховка истекла</b>\n\n"
                "К сожалению, срок действия страховки истёк или лимит замен исчерпан.\n\n"
                "💡 <b>Попробуйте PVNDORA:</b>\n"
                "• Мгновенная доставка\n"
                "• Гарантии на все товары\n"
                "• Партнерская программа 10/7/3%\n"
                "• Круглосуточная поддержка"
            )
            if lang == "ru"
            else (
                "⚠️ <b>Insurance expired</b>\n\n"
                "Unfortunately, your insurance has expired or replacement limit reached.\n\n"
                "💡 <b>Try PVNDORA:</b>\n"
                "• Instant delivery\n"
                "• Warranty on all products\n"
                "• Affiliate program 10/7/3%\n"
                "• 24/7 support"
            )
        )
    else:
        text = (
            (
                "⚠️ <b>Нет страховки</b>\n\n"
                "К сожалению, без страховки замена не предусмотрена.\n\n"
                "💡 <b>Попробуйте PVNDORA:</b>\n"
                "• Мгновенная доставка\n"
                "• Гарантии на все товары\n"
                "• Партнерская программа 10/7/3%\n"
                "• Круглосуточная поддержка"
            )
            if lang == "ru"
            else (
                "⚠️ <b>No insurance</b>\n\n"
                "Unfortunately, no replacement is available without insurance.\n\n"
                "💡 <b>Try PVNDORA:</b>\n"
                "• Instant delivery\n"
                "• Warranty on all products\n"
                "• Affiliate program 10/7/3%\n"
                "• 24/7 support"
            )
        )

    if promo_code:
        text += f"\n\n🎁 <b>Ваш промокод: {promo_code}</b>\n(-50% на первую покупку в PVNDORA)"

    await callback.message.edit_text(
        text,
        reply_markup=get_issue_result_keyboard(has_insurance, can_replace, promo_code, lang),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@router.callback_query(F.data == "discount:replace:confirm")
async def cb_replace_confirm(callback: CallbackQuery, db_user: User):
    """This shouldn't be called directly - replacement happens in issue_type handler."""
    lang = db_user.language_code

    text = (
        ("ℹ️ Для запроса замены выберите заказ и нажмите «Проблема с аккаунтом».")
        if lang == "ru"
        else ("ℹ️ To request a replacement, select an order and click 'Account Problem'.")
    )

    await callback.answer(text, show_alert=True)
