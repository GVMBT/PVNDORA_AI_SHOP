"""Telegram Inline Keyboards"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from core.i18n import get_text


def get_shop_keyboard(lang: str, webapp_url: str) -> InlineKeyboardMarkup:
    """Main shop button that opens the Mini App"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=get_text("btn_shop", lang),
            web_app=WebAppInfo(url=webapp_url)
        )]
    ])


def get_product_keyboard(
    lang: str, 
    product_id: str, 
    webapp_url: str,
    in_stock: bool = True,
    quantity: int = 1
) -> InlineKeyboardMarkup:
    """Product action buttons - always opens Mini App for payment (no extra clicks!)"""
    buttons = []
    
    # WebApp URL - direct to checkout with quantity
    # Format: pay_{product_id}_qty_{quantity}
    checkout_url = f"{webapp_url}?startapp=pay_{product_id}_qty_{quantity}"
    
    if in_stock:
        btn_text = get_text("btn_pay", lang)  # "💳 Оплатить" instead of "💳 Купить"
    else:
        # Pre-order - same flow, just different button text
        btn_text = "💳 Оплатить под заказ" if lang == "ru" else "💳 Pay for Pre-order"
    
    buttons.append([InlineKeyboardButton(
        text=btn_text,
        web_app=WebAppInfo(url=checkout_url)
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_order_keyboard(lang: str, order_id: str) -> InlineKeyboardMarkup:
    """Order action buttons (for support/refund)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=get_text("btn_support", lang),
            callback_data=f"support:{order_id}"
        )],
        [InlineKeyboardButton(
            text=get_text("btn_leave_review", lang),
            callback_data=f"review:{order_id}"
        )]
    ])


def get_payment_keyboard(lang: str, payment_url: str) -> InlineKeyboardMarkup:
    """Payment button"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=get_text("btn_pay", lang),
            url=payment_url
        )]
    ])


def get_cancel_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Cancel action button"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=get_text("btn_cancel", lang),
            callback_data="cancel"
        )]
    ])


def get_checkout_keyboard(lang: str, webapp_url: str) -> InlineKeyboardMarkup:
    """Checkout button - opens Mini App for cart checkout"""
    checkout_url = f"{webapp_url}?startapp=checkout"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="💳 Оплатить заказ" if lang == "ru" else "💳 Pay for Order",
            web_app=WebAppInfo(url=checkout_url)
        )]
    ])

