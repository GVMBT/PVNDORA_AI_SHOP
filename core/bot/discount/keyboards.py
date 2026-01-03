"""Discount bot keyboards - button-based navigation."""
from typing import List, Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

from core.i18n import get_text


# ============================================
# Main Menu
# ============================================

def get_main_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    """Main menu with persistent buttons."""
    catalog_text = "🛒 Каталог" if lang == "ru" else "🛒 Catalog"
    orders_text = "📦 Мои заказы" if lang == "ru" else "📦 My Orders"
    help_text = "❓ Помощь" if lang == "ru" else "❓ Help"
    
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=catalog_text)],
            [KeyboardButton(text=orders_text), KeyboardButton(text=help_text)]
        ],
        resize_keyboard=True,
        is_persistent=True
    )


# ============================================
# Terms Acceptance
# ============================================

def get_terms_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Terms acceptance buttons."""
    accept_text = "✅ Принимаю условия" if lang == "ru" else "✅ Accept Terms"
    read_text = "📄 Прочитать условия" if lang == "ru" else "📄 Read Terms"
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=read_text, callback_data="discount:terms:read")],
        [InlineKeyboardButton(text=accept_text, callback_data="discount:terms:accept")]
    ])


# ============================================
# Catalog
# ============================================

def get_categories_keyboard(categories: List[dict], lang: str) -> InlineKeyboardMarkup:
    """Category selection keyboard."""
    buttons = []
    
    for cat in categories:
        name = cat.get("name_ru" if lang == "ru" else "name", cat.get("name", "Unknown"))
        buttons.append([
            InlineKeyboardButton(
                text=f"📁 {name}",
                callback_data=f"discount:cat:{cat['id'][:8]}"
            )
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_products_keyboard(
    products: List[dict], 
    lang: str,
    category_id: Optional[str] = None,
    page: int = 0,
    page_size: int = 5
) -> InlineKeyboardMarkup:
    """Products list with pagination."""
    buttons = []
    
    start_idx = page * page_size
    end_idx = start_idx + page_size
    page_products = products[start_idx:end_idx]
    
    for p in page_products:
        name = p.get("name", "Product")
        discount_price = p.get("discount_price", 0)
        stock = p.get("available_count", 0)
        
        # Stock indicator
        stock_emoji = "🟢" if stock > 0 else "🟡"
        price_str = f"${discount_price:.0f}" if discount_price else "N/A"
        
        buttons.append([
            InlineKeyboardButton(
                text=f"{stock_emoji} {name} — {price_str}",
                callback_data=f"discount:prod:{p['id'][:8]}"
            )
        ])
    
    # Pagination
    nav_buttons = []
    has_prev = page > 0
    has_next = end_idx < len(products)
    
    if has_prev:
        nav_buttons.append(
            InlineKeyboardButton(text="◀️", callback_data=f"discount:page:{page-1}:{category_id[:8] if category_id else 'all'}")
        )
    
    nav_buttons.append(
        InlineKeyboardButton(text=f"{page+1}/{(len(products)-1)//page_size + 1}", callback_data="noop")
    )
    
    if has_next:
        nav_buttons.append(
            InlineKeyboardButton(text="▶️", callback_data=f"discount:page:{page+1}:{category_id[:8] if category_id else 'all'}")
        )
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    # Back button
    back_text = "⬅️ Назад" if lang == "ru" else "⬅️ Back"
    buttons.append([
        InlineKeyboardButton(text=back_text, callback_data="discount:categories")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ============================================
# Product Card
# ============================================

def get_product_card_keyboard(
    product_id: str,
    discount_price: float,
    insurance_options: List[dict],
    lang: str,
    in_stock: bool = True
) -> InlineKeyboardMarkup:
    """Product card with buy and insurance options."""
    buttons = []
    
    # Buy button
    if in_stock:
        buy_text = f"💳 Купить — ${discount_price:.0f}" if lang == "ru" else f"💳 Buy — ${discount_price:.0f}"
    else:
        buy_text = f"💳 Предзаказ — ${discount_price:.0f}" if lang == "ru" else f"💳 Pre-order — ${discount_price:.0f}"
    
    buttons.append([
        InlineKeyboardButton(
            text=buy_text,
            callback_data=f"discount:buy:{product_id[:8]}:0"  # 0 = no insurance
        )
    ])
    
    # Insurance options
    if insurance_options:
        insurance_header = "🛡 Со страховкой:" if lang == "ru" else "🛡 With Insurance:"
        buttons.append([
            InlineKeyboardButton(text=insurance_header, callback_data="noop")
        ])
        
        for ins in insurance_options:
            ins_id = ins.get("id", "")[:8]
            days = ins.get("duration_days", 7)
            percent = ins.get("price_percent", 50)
            ins_price = discount_price * (1 + percent / 100)
            
            ins_text = f"+{days}д замена — ${ins_price:.0f}" if lang == "ru" else f"+{days}d replacement — ${ins_price:.0f}"
            
            buttons.append([
                InlineKeyboardButton(
                    text=ins_text,
                    callback_data=f"discount:buy:{product_id[:8]}:{ins_id}"
                )
            ])
    
    # Back button
    back_text = "⬅️ К каталогу" if lang == "ru" else "⬅️ To catalog"
    buttons.append([
        InlineKeyboardButton(text=back_text, callback_data="discount:categories")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ============================================
# Payment
# ============================================

def get_payment_keyboard(payment_url: str, lang: str) -> InlineKeyboardMarkup:
    """Payment button."""
    pay_text = "💳 Оплатить" if lang == "ru" else "💳 Pay"
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=pay_text, url=payment_url)]
    ])


def get_order_queued_keyboard(lang: str, order_id: str) -> InlineKeyboardMarkup:
    """Order queued for delivery message."""
    status_text = "📋 Статус заказа" if lang == "ru" else "📋 Order Status"
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=status_text, callback_data=f"discount:status:{order_id[:8]}")]
    ])


# ============================================
# Orders
# ============================================

def get_orders_keyboard(orders: List[dict], lang: str) -> InlineKeyboardMarkup:
    """User orders list."""
    buttons = []
    
    for order in orders[:10]:  # Show last 10
        order_id = order.get("id", "")[:8]
        status = order.get("status", "unknown")
        amount = order.get("amount", 0)
        
        status_emoji = {
            "pending": "⏳",
            "paid": "💳",
            "processing": "⚙️",
            "delivered": "✅",
            "refunded": "↩️",
            "expired": "❌"
        }.get(status, "❓")
        
        buttons.append([
            InlineKeyboardButton(
                text=f"{status_emoji} #{order_id} — ${amount:.0f}",
                callback_data=f"discount:order:{order_id}"
            )
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_order_detail_keyboard(order: dict, lang: str) -> InlineKeyboardMarkup:
    """Order detail actions."""
    order_id = order.get("id", "")[:8]
    status = order.get("status", "")
    has_insurance = order.get("has_insurance", False)
    
    buttons = []
    
    if status == "delivered":
        # Problem button
        problem_text = "⚠️ Проблема с аккаунтом" if lang == "ru" else "⚠️ Account Problem"
        buttons.append([
            InlineKeyboardButton(text=problem_text, callback_data=f"discount:issue:{order_id}")
        ])
        
        # PVNDORA promo
        pvndora_text = "⭐ Перейти в PVNDORA" if lang == "ru" else "⭐ Go to PVNDORA"
        buttons.append([
            InlineKeyboardButton(text=pvndora_text, url="https://t.me/pvndora_ai_bot")
        ])
    
    # Back
    back_text = "⬅️ К заказам" if lang == "ru" else "⬅️ To orders"
    buttons.append([
        InlineKeyboardButton(text=back_text, callback_data="discount:orders")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ============================================
# Issues / Problems
# ============================================

def get_issue_types_keyboard(order_id: str, lang: str) -> InlineKeyboardMarkup:
    """Issue type selection."""
    buttons = []
    
    issues = [
        ("login_failed", "🔐 Не могу войти" if lang == "ru" else "🔐 Can't login"),
        ("banned", "🚫 Аккаунт заблокирован" if lang == "ru" else "🚫 Account banned"),
        ("wrong_product", "❌ Неверный товар" if lang == "ru" else "❌ Wrong product"),
        ("other", "❓ Другое" if lang == "ru" else "❓ Other"),
    ]
    
    for issue_type, text in issues:
        buttons.append([
            InlineKeyboardButton(
                text=text,
                callback_data=f"discount:issue_type:{order_id[:8]}:{issue_type}"
            )
        ])
    
    # Cancel
    cancel_text = "❌ Отмена" if lang == "ru" else "❌ Cancel"
    buttons.append([
        InlineKeyboardButton(text=cancel_text, callback_data=f"discount:order:{order_id[:8]}")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_issue_result_keyboard(
    has_insurance: bool,
    can_replace: bool,
    promo_code: Optional[str],
    lang: str
) -> InlineKeyboardMarkup:
    """Issue resolution options."""
    buttons = []
    
    if has_insurance and can_replace:
        replace_text = "🔄 Получить замену" if lang == "ru" else "🔄 Get Replacement"
        buttons.append([
            InlineKeyboardButton(text=replace_text, callback_data="discount:replace:confirm")
        ])
    
    # PVNDORA offer
    if promo_code:
        pvndora_text = f"⭐ PVNDORA -50% ({promo_code})" if lang == "ru" else f"⭐ PVNDORA -50% ({promo_code})"
    else:
        pvndora_text = "⭐ Попробуй PVNDORA" if lang == "ru" else "⭐ Try PVNDORA"
    
    buttons.append([
        InlineKeyboardButton(text=pvndora_text, url="https://t.me/pvndora_ai_bot")
    ])
    
    # Back to orders
    back_text = "⬅️ К заказам" if lang == "ru" else "⬅️ To orders"
    buttons.append([
        InlineKeyboardButton(text=back_text, callback_data="discount:orders")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ============================================
# Help
# ============================================

def get_help_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Help menu."""
    buttons = []
    
    faq_text = "❓ FAQ" if lang == "ru" else "❓ FAQ"
    payment_text = "💳 Как платить криптой" if lang == "ru" else "💳 How to pay with crypto"
    support_text = "💬 Поддержка" if lang == "ru" else "💬 Support"
    pvndora_text = "⭐ О PVNDORA" if lang == "ru" else "⭐ About PVNDORA"
    
    buttons.append([InlineKeyboardButton(text=faq_text, callback_data="discount:help:faq")])
    buttons.append([InlineKeyboardButton(text=payment_text, callback_data="discount:help:crypto")])
    buttons.append([InlineKeyboardButton(text=support_text, url="https://t.me/pvndora_support")])
    buttons.append([InlineKeyboardButton(text=pvndora_text, url="https://t.me/pvndora_ai_bot")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)
