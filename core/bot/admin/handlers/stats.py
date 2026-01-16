"""Stats Handlers for Admin Bot.

Provides /stats, /users, /stock commands for monitoring.
"""

from datetime import UTC, datetime, timedelta

from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message

from core.logging import get_logger
from core.services.database import get_database

logger = get_logger(__name__)
router = Router(name="stats")


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    """Show general statistics."""
    db = get_database()
    now = datetime.now(UTC)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)

    # Users stats
    users_total_res = await db.client.table("users").select("id", count="exact").execute()  # type: ignore[arg-type]
    users_total = users_total_res.count or 0
    users_today_res = (
        await db.client.table("users")
        .select("id", count="exact")  # type: ignore[arg-type]
        .gte("created_at", today.isoformat())
        .execute()
    )
    users_today = users_today_res.count or 0
    users_week_res = (
        await db.client.table("users")
        .select("id", count="exact")
        .gte("created_at", week_ago.isoformat())
        .execute()
    )
    users_week = users_week_res.count or 0

    # Orders stats
    orders_total_res = await db.client.table("orders").select("id", count="exact").execute()  # type: ignore[arg-type]
    orders_total = orders_total_res.count or 0
    orders_delivered_res = (
        await db.client.table("orders")
        .select("id", count="exact")
        .eq("status", "delivered")
        .execute()
    )
    orders_delivered = orders_delivered_res.count or 0
    orders_today_res = (
        await db.client.table("orders")
        .select("id", count="exact")
        .gte("created_at", today.isoformat())
        .execute()
    )
    orders_today = orders_today_res.count or 0

    # Revenue (delivered orders)
    revenue_result = (
        await db.client.table("orders").select("amount").eq("status", "delivered").execute()
    )
    total_revenue = sum(
        float(o.get("amount", 0)) if isinstance(o, dict) and o.get("amount") is not None else 0.0
        for o in (revenue_result.data or [])
        if isinstance(o, dict)
    )

    # Revenue today
    revenue_today_result = (
        await db.client.table("orders")
        .select("amount")
        .eq("status", "delivered")
        .gte("delivered_at", today.isoformat())
        .execute()
    )
    revenue_today = sum(
        float(o.get("amount", 0)) if isinstance(o, dict) and o.get("amount") is not None else 0.0
        for o in (revenue_today_result.data or [])
        if isinstance(o, dict)
    )

    # Stock stats
    stock_available_res = (
        await db.client.table("stock_items")
        .select("id", count="exact")
        .eq("status", "available")
        .execute()
    )
    stock_available = stock_available_res.count or 0

    # Active partners
    partners_res = (
        await db.client.table("users").select("id", count="exact").eq("is_partner", True).execute()
    )
    partners = partners_res.count or 0

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
        parse_mode=ParseMode.HTML,
    )


@router.message(Command("users"))
async def cmd_users(message: Message) -> None:
    """Show user analytics."""
    db = get_database()
    now = datetime.now(UTC)
    week_ago = now - timedelta(days=7)

    # Language distribution (RPC may not exist, use fallback)
    # lang_result = await db.client.rpc("get_user_language_distribution", {}).execute()

    # Build language stats from users table
    users_result = await db.client.table("users").select("language_code").execute()
    lang_counts: dict[str, int] = {}
    for u in users_result.data or []:
        if isinstance(u, dict):
            lang_raw = u.get("language_code")
            lang = str(lang_raw) if lang_raw is not None else "unknown"
            lang_counts[lang] = lang_counts.get(lang, 0) + 1

    # Sort by count
    sorted_langs = sorted(lang_counts.items(), key=lambda x: x[1], reverse=True)[:8]

    # Active users
    active_count_res = (
        await db.client.table("users")
        .select("id", count="exact")
        .gte("last_activity_at", week_ago.isoformat())
        .execute()
    )
    active_count = active_count_res.count or 0

    # Users with purchases
    # Get unique user_ids from delivered orders
    buyers_result = (
        await db.client.table("orders").select("user_id").eq("status", "delivered").execute()
    )
    unique_buyers = len({o["user_id"] for o in (buyers_result.data or [])})

    # Referral stats
    with_referrers_res = (
        await db.client.table("users")
        .select("id", count="exact")
        .not_.is_("referrer_id", "null")
        .execute()
    )
    with_referrers = with_referrers_res.count or 0

    # Build language distribution text
    lang_lines = []
    lang_flags = {
        "ru": "🇷🇺",
        "en": "🇬🇧",
        "uk": "🇺🇦",
        "de": "🇩🇪",
        "fr": "🇫🇷",
        "es": "🇪🇸",
        "tr": "🇹🇷",
        "ar": "🇸🇦",
        "hi": "🇮🇳",
    }
    for lang, count in sorted_langs:
        flag = lang_flags.get(lang, "🌐")
        lang_lines.append(f"├ {flag} {lang}: <code>{count:,}</code>")

    if lang_lines:
        lang_lines[-1] = lang_lines[-1].replace("├", "└")

    total_users = sum(lang_counts.values())

    await message.answer(
        (
            "◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            "     👥 <b>АНАЛИТИКА ПОЛЬЗОВАТЕЛЕЙ</b>\n"
            "◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            "📊 <b>АКТИВНОСТЬ</b>\n"
            f"├ Всего: <code>{total_users:,}</code>\n"
            f"├ Активных (7д): <code>{active_count:,}</code>\n"
            f"└ С покупками: <code>{unique_buyers:,}</code>\n\n"
            "🌐 <b>ЯЗЫКИ</b>\n" + "\n".join(lang_lines) + "\n\n"
            "🔗 <b>РЕФЕРАЛЫ</b>\n"
            f"└ Пришли по ссылке: <code>{with_referrers:,}</code>\n\n"
            f"<i>Конверсия: {unique_buyers / total_users * 100:.1f}%</i>"
            if total_users
            else ""
        ),
        parse_mode=ParseMode.HTML,
    )


@router.message(Command("stock"))
async def cmd_stock(message: Message) -> None:
    """Show stock status."""
    db = get_database()

    # Get products with stock counts
    products_result = (
        await db.client.table("products")
        .select("id, name, status")
        .eq("status", "active")
        .execute()
    )

    lines = ["◈━━━━━━━━━━━━━━━━━━━━━◈\n     📦 <b>СОСТОЯНИЕ СКЛАДА</b>\n◈━━━━━━━━━━━━━━━━━━━━━◈\n"]

    total_available = 0
    low_stock = []

    for product in products_result.data or []:
        # Count available stock for this product
        stock_count_res = (
            await db.client.table("stock_items")
            .select("id", count="exact")
            .eq("product_id", product["id"])
            .eq("status", "available")
            .execute()
        )
        stock_count = stock_count_res.count or 0

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
        lines.append("\n⚠️ <b>Требует внимания:</b>\n" + "\n".join(f"└ {s}" for s in low_stock[:5]))

    await message.answer("\n".join(lines), parse_mode=ParseMode.HTML)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Show admin commands help."""
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
        parse_mode=ParseMode.HTML,
    )


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    """Welcome message for admin bot."""
    await message.answer(
        "◈━━━━━━━━━━━━━━━━━━━━━◈\n"
        "     🔐 <b>PVNDORA ADMIN</b>\n"
        "◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
        "Добро пожаловать в панель администратора!\n\n"
        "Используйте /help для списка команд.",
        parse_mode=ParseMode.HTML,
    )
