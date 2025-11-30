"""Telegram Inline Keyboards"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from src.i18n import get_text


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
    in_stock: bool = True
) -> InlineKeyboardMarkup:
    """Product action buttons"""
    buttons = []
    
    if in_stock:
        buttons.append([InlineKeyboardButton(
            text=get_text("btn_buy", lang),
            web_app=WebAppInfo(url=f"{webapp_url}?product={product_id}")
        )])
    else:
        buttons.append([InlineKeyboardButton(
            text=get_text("btn_waitlist", lang),
            callback_data=f"waitlist:{product_id}"
        )])
    
    buttons.append([InlineKeyboardButton(
        text=get_text("btn_add_wishlist", lang),
        callback_data=f"wishlist:{product_id}"
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

