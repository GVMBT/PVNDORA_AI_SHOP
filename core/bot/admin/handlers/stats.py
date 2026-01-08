"""
Stats Handlers for Admin Bot

Provides /stats, /users, /stock commands for monitoring.
"""
from datetime import datetime, timezone, timedelta

from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.enums import ParseMode

from core.services.database import get_database
from core.logging import get_logger

logger = get_logger(__name__)
router = Router(name="stats")


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Show general statistics"""
    db = get_database()
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    
    # Users stats
    users_total = db.client.table("users").select("id", count="exact").execute().count or 0
    users_today = db.client.table("users").select("id", count="exact").gte("created_at", today.isoformat()).execute().count or 0
    users_week = db.client.table("users").select("id", count="exact").gte("created_at", week_ago.isoformat()).execute().count or 0
    
    # Orders stats
    orders_total = db.client.table("orders").select("id", count="exact").execute().count or 0
    orders_delivered = db.client.table("orders").select("id", count="exact").eq("status", "delivered").execute().count or 0
    orders_today = db.client.table("orders").select("id", count="exact").gte("created_at", today.isoformat()).execute().count or 0
    
    # Revenue (delivered orders)
    revenue_result = db.client.table("orders").select("amount").eq("status", "delivered").execute()
    total_revenue = sum(float(o.get("amount", 0)) for o in (revenue_result.data or []))
    
    # Revenue today
    revenue_today_result = db.client.table("orders").select("amount").eq("status", "delivered").gte("delivered_at", today.isoformat()).execute()
    revenue_today = sum(float(o.get("amount", 0)) for o in (revenue_today_result.data or []))
    
    # Stock stats
    stock_available = db.client.table("stock_items").select("id", count="exact").eq("status", "available").execute().count or 0
    
    # Active partners
    partners = db.client.table("users").select("id", count="exact").eq("is_partner", True).execute().count or 0
    
    await message.answer(
        "◈━━━━━━━━━━━━━━━━━━━━━◈\n"
        "     📊 <b>СТАТИСТИКА PVNDORA</b>\n"
        "◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
        
        "👥 <b>ПОЛЬЗОВАТЕЛИ</b>\n"
        f"├ Всего: <code>{users_total:,}</code>\n"
        f"├ За сегодня: <code>{users_today:,}</code>\n"
        f"└ За неделю: <code>{users_week:,}</code>\n\n"
        
        "🛒 <b>ЗАКАЗЫ</b>\n"
        f"├ Всего: <code>{orders_total:,}</code>\n"
        f"├ Доставлено: <code>{orders_delivered:,}</code>\n"
        f"└ Сегодня: <code>{orders_today:,}</code>\n\n"
        
        "💰 <b>ВЫРУЧКА</b>\n"
        f"├ Всего: <code>${total_revenue:,.2f}</code>\n"
        f"└ Сегодня: <code>${revenue_today:,.2f}</code>\n\n"
        
        "📦 <b>СКЛАД</b>\n"
        f"└ Доступно: <code>{stock_available:,}</code> шт.\n\n"
        
        "💎 <b>ПАРТНЁРЫ</b>\n"
        f"└ VIP-партнёров: <code>{partners:,}</code>\n\n"
        
        f"<i>Обновлено: {now.strftime('%H:%M UTC')}</i>",
        parse_mode=ParseMode.HTML
    )


@router.message(Command("users"))
async def cmd_users(message: Message):
    """Show user analytics"""
    db = get_database()
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    
    # Language distribution
    lang_result = db.client.rpc("get_user_language_distribution", {}).execute()
    
    # Build language stats from users table
    users_result = db.client.table("users").select("language_code").execute()
    lang_counts: dict = {}
    for u in (users_result.data or []):
        lang = u.get("language_code") or "unknown"
        lang_counts[lang] = lang_counts.get(lang, 0) + 1
    
    # Sort by count
    sorted_langs = sorted(lang_counts.items(), key=lambda x: x[1], reverse=True)[:8]
    
    # Active users
    active_count = db.client.table("users").select("id", count="exact").gte("last_activity_at", week_ago.isoformat()).execute().count or 0
    
    # Users with purchases
    # Get unique user_ids from delivered orders
    buyers_result = db.client.table("orders").select("user_id").eq("status", "delivered").execute()
    unique_buyers = len(set(o["user_id"] for o in (buyers_result.data or [])))
    
    # Referral stats
    with_referrers = db.client.table("users").select("id", count="exact").not_.is_("referrer_id", "null").execute().count or 0
    
    # Build language distribution text
    lang_lines = []
    lang_flags = {
        "ru": "🇷🇺", "en": "🇬🇧", "uk": "🇺🇦", "de": "🇩🇪",
        "fr": "🇫🇷", "es": "🇪🇸", "tr": "🇹🇷", "ar": "🇸🇦", "hi": "🇮🇳"
    }
    for lang, count in sorted_langs:
        flag = lang_flags.get(lang, "🌐")
        lang_lines.append(f"├ {flag} {lang}: <code>{count:,}</code>")
    
    if lang_lines:
        lang_lines[-1] = lang_lines[-1].replace("├", "└")
    
    total_users = sum(lang_counts.values())
    
    await message.answer(
        "◈━━━━━━━━━━━━━━━━━━━━━◈\n"
        "     👥 <b>АНАЛИТИКА ПОЛЬЗОВАТЕЛЕЙ</b>\n"
        "◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
        
        "📊 <b>АКТИВНОСТЬ</b>\n"
        f"├ Всего: <code>{total_users:,}</code>\n"
        f"├ Активных (7д): <code>{active_count:,}</code>\n"
        f"└ С покупками: <code>{unique_buyers:,}</code>\n\n"
        
        "🌐 <b>ЯЗЫКИ</b>\n"
        + "\n".join(lang_lines) + "\n\n"
        
        "🔗 <b>РЕФЕРАЛЫ</b>\n"
        f"└ Пришли по ссылке: <code>{with_referrers:,}</code>\n\n"
        
        f"<i>Конверсия: {unique_buyers/total_users*100:.1f}%</i>" if total_users else "",
        parse_mode=ParseMode.HTML
    )


@router.message(Command("stock"))
async def cmd_stock(message: Message):
    """Show stock status"""
    db = get_database()
    
    # Get products with stock counts
    products_result = db.client.table("products").select("id, name, status").eq("status", "active").execute()
    
    lines = [
        "◈━━━━━━━━━━━━━━━━━━━━━◈\n"
        "     📦 <b>СОСТОЯНИЕ СКЛАДА</b>\n"
        "◈━━━━━━━━━━━━━━━━━━━━━◈\n"
    ]
    
    total_available = 0
    low_stock = []
    
    for product in (products_result.data or []):
        # Count available stock for this product
        stock_count = db.client.table("stock_items").select("id", count="exact").eq("product_id", product["id"]).eq("status", "available").execute().count or 0
        
        total_available += stock_count
        
        # Status indicator
        if stock_count == 0:
            indicator = "🔴"
            low_stock.append(product["name"])
        elif stock_count < 5:
            indicator = "🟡"
            low_stock.append(f"{product['name']} ({stock_count})")
        else:
            indicator = "🟢"
        
        lines.append(f"{indicator} <b>{product['name']}</b>: <code>{stock_count}</code>")
    
    lines.append(f"\n📊 <b>Всего доступно:</b> <code>{total_available}</code>")
    
    if low_stock:
        lines.append(f"\n⚠️ <b>Требует внимания:</b>\n" + "\n".join(f"└ {s}" for s in low_stock[:5]))
    
    await message.answer("\n".join(lines), parse_mode=ParseMode.HTML)


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Show admin commands help"""
    await message.answer(
        "◈━━━━━━━━━━━━━━━━━━━━━◈\n"
        "     🤖 <b>ADMIN BOT</b>\n"
        "◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
        
        "📢 <b>РАССЫЛКИ</b>\n"
        "├ /broadcast — Создать рассылку\n"
        "└ /broadcasts — Список рассылок\n\n"
        
        "📊 <b>СТАТИСТИКА</b>\n"
        "├ /stats — Общая статистика\n"
        "├ /users — Аналитика пользователей\n"
        "└ /stock — Состояние склада\n\n"
        
        "<i>PVNDORA Admin Panel</i>",
        parse_mode=ParseMode.HTML
    )


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Welcome message for admin bot"""
    await message.answer(
        "◈━━━━━━━━━━━━━━━━━━━━━◈\n"
        "     🔐 <b>PVNDORA ADMIN</b>\n"
        "◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
        
        "Добро пожаловать в панель администратора!\n\n"
        
        "Используйте /help для списка команд.",
        parse_mode=ParseMode.HTML
    )
