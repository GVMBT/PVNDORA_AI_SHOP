"""Discount bot issue/problem handlers.
All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""

from typing import Any, cast

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.types import CallbackQuery

from core.logging import get_logger
from core.services.database import User, get_database
from core.services.domains import InsuranceService, PromoCodeService, PromoTriggers

from ..keyboards import get_issue_result_keyboard, get_issue_types_keyboard

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


async def get_order_item_with_insurance(db, order_short_id: str) -> dict[str, Any] | None:
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

        item = cast(dict[str, Any], items_result.data[0])
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


# Helper: Generate promo code based on trigger (reduces cognitive complexity)
async def _generate_promo_for_issue(
    promo_service: PromoCodeService,
    user_id: str,
    telegram_id: int,
    trigger: PromoTriggers,
) -> str | None:
    """Generate or get existing promo code for issue trigger."""
    existing_promo = await promo_service.get_promo_by_trigger(user_id, trigger)
    if existing_promo:
        return existing_promo.code
    promo = await promo_service.generate_personal_promo(
        user_id=user_id,
        telegram_id=telegram_id,
        trigger=trigger,
        discount_percent=50,
    )
    return promo


# Helper: Get issue reason from type (reduces cognitive complexity)
def _get_issue_reason(issue_type: str) -> str:
    """Map issue type to reason string."""
    reason_map = {
        "login_failed": "Cannot login to account",
        "banned": "Account was banned",
        "wrong_product": "Received wrong product",
        "other": "Other issue",
    }
    return reason_map.get(issue_type, issue_type)


# Helper: Handle replacement request (reduces cognitive complexity)
async def _handle_replacement_request(
    insurance_service: InsuranceService,
    order_item: dict,
    telegram_id: int,
    reason: str,
    lang: str,
    callback: CallbackQuery,
) -> tuple[bool, dict | None]:
    """Handle replacement request, return (success, result_dict)."""
    result = await insurance_service.request_replacement(
        order_item_id=order_item["id"], telegram_id=telegram_id, reason=reason
    )

    if not result.success:
        result_dict = {"success": False, "status": result.status, "message": result.message}
        return False, result_dict

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
    return True, None


# Helper: Get promo code based on insurance status (reduces cognitive complexity)
async def _get_promo_for_insurance_status(
    promo_service: PromoCodeService,
    order_item: dict,
    telegram_id: int,
    has_insurance: bool,
    can_replace: bool,
    replacement_result: dict | None = None,
) -> str | None:
    """Get promo code based on insurance and replacement status."""
    if not has_insurance:
        return await _generate_promo_for_issue(
            promo_service,
            order_item["user_id"],
            telegram_id,
            PromoTriggers.ISSUE_NO_INSURANCE,
        )

    if has_insurance and not can_replace:
        # Check if replacement failed due to limit
        replacement_status = replacement_result.get("status") if replacement_result else None
        replacement_message = (
            (replacement_result.get("message") or "").lower() if replacement_result else ""
        )
        if replacement_status == "rejected" and "limit" in replacement_message:
            return await _generate_promo_for_issue(
                promo_service,
                order_item["user_id"],
                telegram_id,
                PromoTriggers.REPLACEMENT_LIMIT,
            )

        # Insurance expired
        return await _generate_promo_for_issue(
            promo_service,
            order_item["user_id"],
            telegram_id,
            PromoTriggers.INSURANCE_EXPIRED,
        )

    return None


# Helper: Get message text for issue result (reduces cognitive complexity)
def _get_issue_result_message(has_insurance: bool, can_replace: bool, lang: str) -> str:
    """Get message text based on insurance and replacement status."""
    pvndora_pitch = (
        "💡 <b>Попробуйте PVNDORA:</b>\n"
        "• Мгновенная доставка\n"
        "• Гарантии на все товары\n"
        "• Партнерская программа 10/7/3%\n"
        "• Круглосуточная поддержка"
        if lang == "ru"
        else "💡 <b>Try PVNDORA:</b>\n"
        "• Instant delivery\n"
        "• Warranty on all products\n"
        "• Affiliate program 10/7/3%\n"
        "• 24/7 support"
    )

    if has_insurance and not can_replace:
        header = (
            "⚠️ <b>Страховка истекла</b>\n\n"
            "К сожалению, срок действия страховки истёк или лимит замен исчерпан.\n\n"
            if lang == "ru"
            else "⚠️ <b>Insurance expired</b>\n\n"
            "Unfortunately, your insurance has expired or replacement limit reached.\n\n"
        )
    else:
        header = (
            "⚠️ <b>Нет страховки</b>\n\nК сожалению, без страховки замена не предусмотрена.\n\n"
            if lang == "ru"
            else "⚠️ <b>No insurance</b>\n\n"
            "Unfortunately, no replacement is available without insurance.\n\n"
        )

    return f"{header}{pvndora_pitch}"


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

    reason = _get_issue_reason(issue_type)

    # Check insurance
    insurance_service = InsuranceService(db.client)
    promo_service = PromoCodeService(db.client)

    has_insurance = order_item.get("insurance_id") is not None
    can_replace = False
    replacement_result = None
    if has_insurance:
        # Check if insurance is valid and replacements available
        is_valid, _, remaining = await insurance_service.check_insurance_valid(order_item["id"])
        can_replace = is_valid and remaining > 0

        if can_replace:
            # Try to request replacement
            success, result = await _handle_replacement_request(
                insurance_service, order_item, db_user.telegram_id, reason, lang, callback
            )
            if success:
                return

            # Replacement failed - store result for promo code logic
            can_replace = False
            replacement_result = result

    # Get promo code based on status
    promo_code = await _get_promo_for_insurance_status(
        promo_service,
        order_item,
        db_user.telegram_id,
        has_insurance,
        can_replace,
        replacement_result,
    )

    # Show result message
    text = _get_issue_result_message(has_insurance, can_replace, lang)

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
