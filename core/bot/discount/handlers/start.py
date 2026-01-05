"""Discount bot /start and terms handlers."""
from datetime import datetime, timezone

from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.enums import ParseMode

from core.services.database import User, get_database
from core.logging import get_logger
from ..keyboards import get_main_menu_keyboard, get_terms_keyboard, get_help_keyboard

logger = get_logger(__name__)

router = Router(name="discount_start")


@router.message(CommandStart())
async def cmd_start(message: Message, db_user: User, bot: Bot):
    """Handle /start command with terms prompt."""
    lang = db_user.language_code
    db = get_database()
    
    # Check if terms already accepted
    try:
        result = db.client.table("users").select(
            "terms_accepted"
        ).eq("id", db_user.id).single().execute()
        
        terms_accepted = result.data.get("terms_accepted", False) if result.data else False
    except Exception:
        terms_accepted = False
    
    if terms_accepted:
        # Welcome back message
        text = (
            "👋 <b>Добро пожаловать!</b>\n\n"
            "Выберите раздел в меню ниже."
        ) if lang == "ru" else (
            "👋 <b>Welcome!</b>\n\n"
            "Choose a section from the menu below."
        )
        
        await message.answer(
            text,
            reply_markup=get_main_menu_keyboard(lang),
            parse_mode=ParseMode.HTML
        )
    else:
        # Show terms
        text = (
            "📜 <b>Добро пожаловать!</b>\n\n"
            "Перед использованием бота ознакомьтесь с условиями:\n\n"
            "• Мы предоставляем доступ к ознакомительным версиям сервисов\n"
            "• Замены доступны только при наличии страховки\n"
            "• Мы не несем ответственности за использование аккаунтов\n"
            "• Доставка в течение 1-4 часов после оплаты\n\n"
            "Нажмите кнопку ниже, чтобы принять условия."
        ) if lang == "ru" else (
            "📜 <b>Welcome!</b>\n\n"
            "Before using the bot, please review the terms:\n\n"
            "• We provide access to trial versions of services\n"
            "• Replacements available only with insurance\n"
            "• We are not responsible for account usage\n"
            "• Delivery within 1-4 hours after payment\n\n"
            "Click the button below to accept."
        )
        
        await message.answer(
            text,
            reply_markup=get_terms_keyboard(lang),
            parse_mode=ParseMode.HTML
        )


@router.callback_query(F.data == "discount:terms:read")
async def cb_terms_read(callback: CallbackQuery, db_user: User):
    """Show full terms text."""
    lang = db_user.language_code
    
    text = (
        "📜 <b>Полные условия использования</b>\n\n"
        "<b>1. Предмет соглашения</b>\n"
        "Мы предоставляем доступ к ознакомительным версиям AI-сервисов. "
        "Товары предназначены для личного использования.\n\n"
        "<b>2. Гарантии и замены</b>\n"
        "• Без страховки: замена не предоставляется\n"
        "• Со страховкой: замена в рамках срока действия\n"
        "• Лимит замен: указан при покупке\n\n"
        "<b>3. Доставка</b>\n"
        "Товар доставляется в течение 1-4 часов после оплаты.\n\n"
        "<b>4. Ограничение ответственности</b>\n"
        "Мы не несем ответственности за:\n"
        "• Блокировку аккаунтов по вине пользователя\n"
        "• Нарушение условий использования сервисов\n"
        "• Потерю данных пользователя\n\n"
        "<b>5. Возвраты</b>\n"
        "Возврат средств не предусмотрен после получения товара.\n\n"
        "Нажмите «Принимаю условия» для продолжения."
    ) if lang == "ru" else (
        "📜 <b>Full Terms of Service</b>\n\n"
        "<b>1. Subject of Agreement</b>\n"
        "We provide access to trial versions of AI services. "
        "Products are for personal use only.\n\n"
        "<b>2. Warranties and Replacements</b>\n"
        "• Without insurance: no replacement provided\n"
        "• With insurance: replacement within validity period\n"
        "• Replacement limit: as specified at purchase\n\n"
        "<b>3. Delivery</b>\n"
        "Products are delivered within 1-4 hours after payment.\n\n"
        "<b>4. Limitation of Liability</b>\n"
        "We are not responsible for:\n"
        "• Account bans due to user actions\n"
        "• Violation of service terms\n"
        "• User data loss\n\n"
        "<b>5. Refunds</b>\n"
        "No refunds after product delivery.\n\n"
        "Click 'Accept Terms' to continue."
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_terms_keyboard(lang),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data == "discount:terms:accept")
async def cb_terms_accept(callback: CallbackQuery, db_user: User):
    """Accept terms and show main menu."""
    lang = db_user.language_code
    db = get_database()
    
    # Update terms_accepted
    try:
        db.client.table("users").update({
            "terms_accepted": True,
            "terms_accepted_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", db_user.id).execute()
        
        logger.info(f"User {db_user.telegram_id} accepted terms")
    except Exception as e:
        logger.error(f"Failed to save terms acceptance: {e}")
    
    # Show welcome message
    text = (
        "✅ <b>Условия приняты!</b>\n\n"
        "Добро пожаловать! Выберите раздел в меню ниже."
    ) if lang == "ru" else (
        "✅ <b>Terms accepted!</b>\n\n"
        "Welcome! Choose a section from the menu below."
    )
    
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML)
    await callback.message.answer(
        "👇",
        reply_markup=get_main_menu_keyboard(lang)
    )
    await callback.answer()


@router.callback_query(F.data == "discount:check_sub")
async def cb_check_subscription(callback: CallbackQuery, db_user: User, bot: Bot):
    """Re-check channel subscription."""
    from ..middlewares import REQUIRED_CHANNEL
    
    lang = db_user.language_code
    
    try:
        member = await bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=db_user.telegram_id)
        
        if member.status in ("left", "kicked"):
            await callback.answer(
                "Вы ещё не подписались на канал!" if lang == "ru" else "You haven't subscribed yet!",
                show_alert=True
            )
            return
        
        # Subscribed - show start
        await callback.message.delete()
        
        text = (
            "✅ <b>Подписка подтверждена!</b>\n\n"
            "Добро пожаловать! Нажмите /start для начала."
        ) if lang == "ru" else (
            "✅ <b>Subscription confirmed!</b>\n\n"
            "Welcome! Press /start to begin."
        )
        
        await callback.message.answer(text, parse_mode=ParseMode.HTML)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Failed to check subscription: {e}")
        await callback.answer("Ошибка проверки" if lang == "ru" else "Check error", show_alert=True)


@router.message(Command("help"))
async def cmd_help(message: Message, db_user: User):
    """Handle /help command."""
    lang = db_user.language_code
    
    text = (
        "❓ <b>Помощь</b>\n\n"
        "Выберите раздел:"
    ) if lang == "ru" else (
        "❓ <b>Help</b>\n\n"
        "Choose a section:"
    )
    
    await message.answer(text, reply_markup=get_help_keyboard(lang), parse_mode=ParseMode.HTML)


@router.message(F.text.in_(["❓ Помощь", "❓ Help"]))
async def msg_help(message: Message, db_user: User):
    """Handle help button."""
    await cmd_help(message, db_user)


@router.callback_query(F.data == "discount:help:faq")
async def cb_help_faq(callback: CallbackQuery, db_user: User):
    """Show FAQ."""
    lang = db_user.language_code
    
    text = (
        "❓ <b>Часто задаваемые вопросы</b>\n\n"
        "<b>Q: Как быстро придет заказ?</b>\n"
        "A: Доставка в течение 1-4 часов после оплаты.\n\n"
        "<b>Q: Что делать если аккаунт не работает?</b>\n"
        "A: Если у вас есть страховка - нажмите «Проблема» в заказе. "
        "Без страховки замена не предоставляется.\n\n"
        "<b>Q: Можно ли вернуть деньги?</b>\n"
        "A: Возврат не предусмотрен после получения товара.\n\n"
        "<b>Q: Что такое PVNDORA?</b>\n"
        "A: Наш премиум-сервис с мгновенной доставкой, гарантиями и "
        "партнерской программой 10/7/3%."
    ) if lang == "ru" else (
        "❓ <b>Frequently Asked Questions</b>\n\n"
        "<b>Q: How fast will I receive my order?</b>\n"
        "A: Delivery within 1-4 hours after payment.\n\n"
        "<b>Q: What if the account doesn't work?</b>\n"
        "A: If you have insurance - click 'Problem' in your order. "
        "Without insurance, no replacement is provided.\n\n"
        "<b>Q: Can I get a refund?</b>\n"
        "A: No refunds after product delivery.\n\n"
        "<b>Q: What is PVNDORA?</b>\n"
        "A: Our premium service with instant delivery, guarantees, and "
        "affiliate program 10/7/3%."
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_help_keyboard(lang),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data == "discount:help:crypto")
async def cb_help_crypto(callback: CallbackQuery, db_user: User):
    """Show crypto payment guide."""
    lang = db_user.language_code
    
    text = (
        "💳 <b>Как платить криптой</b>\n\n"
        "<b>Шаг 1:</b> Выберите товар и нажмите «Купить»\n\n"
        "<b>Шаг 2:</b> На странице оплаты выберите «Crypto»\n\n"
        "<b>Шаг 3:</b> Выберите криптовалюту (BTC, ETH, USDT и др.)\n\n"
        "<b>Шаг 4:</b> Отправьте точную сумму на указанный адрес\n\n"
        "<b>Шаг 5:</b> Дождитесь подтверждения сети (обычно 1-30 мин)\n\n"
        "⚠️ Отправляйте <b>точную сумму</b> одной транзакцией!\n"
        "Неверная сумма = потеря средств."
    ) if lang == "ru" else (
        "💳 <b>How to Pay with Crypto</b>\n\n"
        "<b>Step 1:</b> Select a product and click 'Buy'\n\n"
        "<b>Step 2:</b> On the payment page, select 'Crypto'\n\n"
        "<b>Step 3:</b> Choose cryptocurrency (BTC, ETH, USDT, etc.)\n\n"
        "<b>Step 4:</b> Send the exact amount to the provided address\n\n"
        "<b>Step 5:</b> Wait for network confirmation (usually 1-30 min)\n\n"
        "⚠️ Send the <b>exact amount</b> in a single transaction!\n"
        "Wrong amount = lost funds."
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_help_keyboard(lang),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()
