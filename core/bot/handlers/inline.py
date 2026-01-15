"""Inline query handlers for product sharing."""

import hashlib

from aiogram import Bot, Router
from aiogram.enums import ParseMode
from aiogram.types import (
    ChosenInlineResult,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
)

from core.bot.handlers.helpers import WEBAPP_URL
from core.logging import get_logger
from core.services.database import User, get_database

logger = get_logger(__name__)

router = Router()


@router.inline_query()
async def handle_inline_query(query: InlineQuery, db_user: User, bot: Bot) -> None:
    """Handle inline queries for product sharing and search."""
    if db_user is None:
        await query.answer([], cache_time=0)
        return

    query_text = query.query.strip()
    bot_info = await bot.get_me()
    user_telegram_id = query.from_user.id
    referral_link = f"https://t.me/{bot_info.username}?start=ref_{user_telegram_id}"

    results = []

    if not query_text or query_text.lower() == "invite":
        # Default: show sharing options
        total_saved = (
            float(db_user.total_saved)
            if hasattr(db_user, "total_saved") and db_user.total_saved
            else 0
        )

        results.append(
            InlineQueryResultArticle(
                id=f"invite_{db_user.id}",
                title="🎁 Пригласить друга",
                description=f"Я сэкономил {int(total_saved)}₽. Поделись ссылкой!",
                thumbnail_url=f"{WEBAPP_URL}/assets/share-preview.png",
                input_message_content=InputTextMessageContent(
                    message_text=(
                        f"🚀 <b>Я уже сэкономил {int(total_saved)}₽ на AI-подписках с PVNDORA!</b>\n\n"
                        f"Присоединяйся и получай доступ к лучшим AI-сервисам 👇"
                    ),
                    parse_mode=ParseMode.HTML,
                ),
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🛍 Перейти в магазин", url=referral_link)],
                    ],
                ),
            ),
        )

        results.append(
            InlineQueryResultArticle(
                id="share_catalog",
                title="🛍 Поделиться каталогом",
                description="Отправить ссылку на каталог друзьям",
                input_message_content=InputTextMessageContent(
                    message_text=(
                        "🛍 <b>PVNDORA Каталог</b>\n\n"
                        "Премиум AI-подписки:\n✅ Лучшие цены\n✅ Мгновенная доставка\n✅ Гарантия включена\n\nСмотри! 👇"
                    ),
                    parse_mode=ParseMode.HTML,
                ),
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🛍 Открыть каталог", url=referral_link)],
                    ],
                ),
            ),
        )
    else:
        # Search products to share
        try:
            db = get_database()
            products = await db.search_products(query_text)

            for product in products:
                # Use SHA256 for ID generation (MD5 is cryptographically insecure)
                result_id = hashlib.sha256(f"{product.id}:{user_telegram_id}".encode()).hexdigest()[
                    :16
                ]
                product_link = f"https://t.me/{bot_info.username}?start=product_{product.id}_ref_{user_telegram_id}"
                description = (product.description or "")[:100]

                results.append(
                    InlineQueryResultArticle(
                        id=result_id,
                        title=f"📦 {product.name}",
                        description=f"{description}... • {product.price:.0f}₽",
                        input_message_content=InputTextMessageContent(
                            message_text=(
                                f"📦 <b>{product.name}</b>\n\n{description}\n\n"
                                f"💰 Цена: <b>{product.price:.0f}₽</b>\n\n🛒 Купить здесь:"
                            ),
                            parse_mode=ParseMode.HTML,
                        ),
                        reply_markup=InlineKeyboardMarkup(
                            inline_keyboard=[
                                [
                                    InlineKeyboardButton(
                                        text=f"Купить {product.name}", url=product_link,
                                    ),
                                ],
                            ],
                        ),
                    ),
                )
        except Exception as e:
            logger.error(f"Inline product search failed: {e}", exc_info=True)
            results.append(
                InlineQueryResultArticle(
                    id="search_fallback",
                    title=f"🔍 Найти: {query_text}",
                    description="Поиск в PVNDORA",
                    input_message_content=InputTextMessageContent(
                        message_text=f"🔍 Ищете <b>{query_text}</b>?\n\nНайдите лучшие AI-подписки в PVNDORA!",
                        parse_mode=ParseMode.HTML,
                    ),
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[
                            [InlineKeyboardButton(text="🔍 Искать в PVNDORA", url=referral_link)],
                        ],
                    ),
                ),
            )

    await query.answer(results, cache_time=300, is_personal=True)


@router.chosen_inline_result()
async def handle_chosen_inline_result(chosen_result: ChosenInlineResult, db_user: User) -> None:
    """Track when user sends an inline result for analytics."""
    try:
        db = get_database()
        await db.log_event(
            user_id=db_user.id if db_user else None,
            event_type="share",
            metadata={"result_id": chosen_result.result_id, "query": chosen_result.query},
        )
    except Exception:
        pass
