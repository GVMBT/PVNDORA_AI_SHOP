"""
Broadcast Handlers for Admin Bot

Implements the /broadcast command and FSM flow for creating mailings.
"""
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest

from core.services.database import get_database
from core.logging import get_logger
from ..states import BroadcastStates

logger = get_logger(__name__)
router = Router(name="broadcast")


async def safe_edit_text(callback: CallbackQuery, text: str, **kwargs) -> bool:
    """
    Safely edit message text, ignoring 'message is not modified' errors.
    Returns True if edited successfully, False if message was not modified.
    """
    try:
        await callback.message.edit_text(text, **kwargs)
        return True
    except TelegramBadRequest as e:
        error_msg = str(e).lower()
        if "message is not modified" in error_msg:
            # Message already has the same content - not an error
            logger.debug(f"Message not modified (already correct): {callback.data}")
            return False
        # Re-raise other BadRequest errors
        raise
    except Exception as e:
        logger.error(f"Failed to edit message: {e}")
        raise

# Constants
TARGET_BOTS = {
    "pvndora": "🤖 PVNDORA (Premium)",
    "discount": "💸 Discount Bot"
}

AUDIENCES = {
    "all": "👥 Все пользователи",
    "active": "🟢 Активные (7 дней)",
    "inactive": "⚪ Неактивные (7+ дней)",
    "vip": "💎 VIP-партнёры",
    "buyers": "🛒 С покупками",
    "non_buyers": "👀 Без покупок"
}

LANGUAGES = ["ru", "en", "uk", "de", "fr", "es", "tr", "ar", "hi"]
LANGUAGE_FLAGS = {
    "ru": "🇷🇺", "en": "🇬🇧", "uk": "🇺🇦", "de": "🇩🇪",
    "fr": "🇫🇷", "es": "🇪🇸", "tr": "🇹🇷", "ar": "🇸🇦", "hi": "🇮🇳"
}


def get_bot_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting target bot"""
    buttons = [
        [InlineKeyboardButton(text=name, callback_data=f"bc:bot:{key}")]
        for key, name in TARGET_BOTS.items()
    ]
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="bc:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_audience_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting audience"""
    buttons = [
        [InlineKeyboardButton(text=name, callback_data=f"bc:aud:{key}")]
        for key, name in AUDIENCES.items()
    ]
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="bc:back:bot")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_languages_keyboard(selected: List[str]) -> InlineKeyboardMarkup:
    """Keyboard for selecting languages (toggle)"""
    buttons = []
    row = []
    for lang in LANGUAGES:
        flag = LANGUAGE_FLAGS.get(lang, "🌐")
        check = "✅" if lang in selected else ""
        row.append(InlineKeyboardButton(
            text=f"{flag} {lang.upper()} {check}",
            callback_data=f"bc:lang:{lang}"
        ))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    
    # All languages button
    all_check = "✅" if not selected else ""
    buttons.append([InlineKeyboardButton(
        text=f"🌐 Все языки {all_check}",
        callback_data="bc:lang:all"
    )])
    
    buttons.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="bc:back:audience"),
        InlineKeyboardButton(text="✅ Далее", callback_data="bc:lang:done")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_content_keyboard(languages: List[str], current_lang: str, filled: Dict[str, bool]) -> InlineKeyboardMarkup:
    """Keyboard showing content status per language"""
    buttons = []
    row = []
    for lang in languages:
        flag = LANGUAGE_FLAGS.get(lang, "🌐")
        status = "✅" if filled.get(lang) else "📝"
        is_current = "👉" if lang == current_lang else ""
        row.append(InlineKeyboardButton(
            text=f"{is_current}{flag} {status}",
            callback_data=f"bc:content:{lang}"
        ))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    
    # Navigation
    all_filled = all(filled.get(l) for l in languages)
    nav_row = [InlineKeyboardButton(text="◀️ Назад", callback_data="bc:back:languages")]
    if all_filled:
        nav_row.append(InlineKeyboardButton(text="✅ Готово", callback_data="bc:content:done"))
    buttons.append(nav_row)
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_media_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for media upload step"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустить медиа", callback_data="bc:media:skip")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="bc:back:content")]
    ])


def get_buttons_keyboard(has_buttons: bool) -> InlineKeyboardMarkup:
    """Keyboard for buttons step"""
    buttons = []
    if has_buttons:
        buttons.append([InlineKeyboardButton(text="➕ Добавить ещё", callback_data="bc:btn:add")])
        buttons.append([InlineKeyboardButton(text="✅ Готово с кнопками", callback_data="bc:btn:done")])
    else:
        buttons.append([InlineKeyboardButton(text="⏭ Без кнопок", callback_data="bc:btn:skip")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="bc:back:media")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_preview_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for preview step"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👁 Превью RU", callback_data="bc:preview:ru"),
            InlineKeyboardButton(text="👁 Превью EN", callback_data="bc:preview:en")
        ],
        [InlineKeyboardButton(text="🚀 Отправить сейчас", callback_data="bc:send:now")],
        [InlineKeyboardButton(text="⏰ Запланировать", callback_data="bc:schedule")],
        [
            InlineKeyboardButton(text="◀️ Изменить", callback_data="bc:back:buttons"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="bc:cancel")
        ]
    ])


# ==================== COMMANDS ====================

@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, state: FSMContext):
    """Start broadcast creation flow"""
    await state.clear()
    
    await state.update_data(
        target_bot=None,
        target_audience=None,
        target_languages=[],
        content={},
        media_type=None,
        media_file_id=None,
        buttons=[]
    )
    
    await message.answer(
        "◈━━━━━━━━━━━━━━━━━━━━━◈\n"
        "     📢 <b>НОВАЯ РАССЫЛКА</b>\n"
        "◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
        "🤖 <b>Шаг 1/6:</b> Выберите бота для рассылки:",
        parse_mode=ParseMode.HTML,
        reply_markup=get_bot_keyboard()
    )
    await state.set_state(BroadcastStates.select_bot)


@router.message(Command("broadcasts"))
async def cmd_broadcasts_list(message: Message):
    """List recent broadcasts"""
    db = get_database()
    
    result = db.client.table("broadcast_messages").select(
        "id, slug, target_bot, status, sent_count, total_recipients, created_at"
    ).order("created_at", desc=True).limit(10).execute()
    
    if not result.data:
        await message.answer("📭 Нет рассылок")
        return
    
    lines = ["◈━━━━━━━━━━━━━━━━━━━━━◈\n     📢 <b>РАССЫЛКИ</b>\n◈━━━━━━━━━━━━━━━━━━━━━◈\n"]
    
    status_icons = {
        "draft": "📝",
        "scheduled": "⏰",
        "sending": "🔄",
        "sent": "✅",
        "cancelled": "❌"
    }
    
    for bc in result.data:
        icon = status_icons.get(bc["status"], "❓")
        bot_icon = "🤖" if bc["target_bot"] == "pvndora" else "💸"
        progress = f"{bc['sent_count']}/{bc['total_recipients']}" if bc["total_recipients"] else "—"
        lines.append(f"{icon} {bot_icon} <code>{bc['slug'] or bc['id'][:8]}</code> — {progress}")
    
    await message.answer("\n".join(lines), parse_mode=ParseMode.HTML)


# ==================== CALLBACKS: BOT SELECTION ====================

@router.callback_query(BroadcastStates.select_bot, F.data.startswith("bc:bot:"))
async def cb_select_bot(callback: CallbackQuery, state: FSMContext):
    """Handle bot selection"""
    bot_key = callback.data.split(":")[-1]
    
    if bot_key not in TARGET_BOTS:
        await callback.answer("Неизвестный бот", show_alert=True)
        return
    
    await state.update_data(target_bot=bot_key)
    
    await safe_edit_text(
        callback,
        "◈━━━━━━━━━━━━━━━━━━━━━◈\n"
        "     📢 <b>НОВАЯ РАССЫЛКА</b>\n"
        "◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
        f"🤖 Бот: <b>{TARGET_BOTS.get(bot_key, bot_key)}</b>\n\n"
        "🎯 <b>Шаг 2/6:</b> Выберите аудиторию:",
        parse_mode=ParseMode.HTML,
        reply_markup=get_audience_keyboard()
    )
    await state.set_state(BroadcastStates.select_audience)
    await callback.answer()


# ==================== CALLBACKS: AUDIENCE SELECTION ====================

@router.callback_query(BroadcastStates.select_audience, F.data.startswith("bc:aud:"))
async def cb_select_audience(callback: CallbackQuery, state: FSMContext):
    """Handle audience selection"""
    aud_key = callback.data.split(":")[-1]
    
    if aud_key not in AUDIENCES:
        await callback.answer("Неизвестная аудитория", show_alert=True)
        return
    
    data = await state.get_data()
    await state.update_data(target_audience=aud_key)
    
    target_bot = data.get("target_bot", "?")
    
    await safe_edit_text(callback,
        "◈━━━━━━━━━━━━━━━━━━━━━◈\n"
        "     📢 <b>НОВАЯ РАССЫЛКА</b>\n"
        "◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
        f"🤖 Бот: <b>{TARGET_BOTS.get(target_bot, target_bot)}</b>\n"
        f"🎯 Аудитория: <b>{AUDIENCES.get(aud_key, aud_key)}</b>\n\n"
        "🌐 <b>Шаг 3/6:</b> Выберите языки:\n"
        "<i>(можно выбрать несколько)</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=get_languages_keyboard([])
    )
    await state.set_state(BroadcastStates.select_languages)
    await callback.answer()


# ==================== CALLBACKS: LANGUAGE SELECTION ====================

@router.callback_query(BroadcastStates.select_languages, F.data.startswith("bc:lang:"))
async def cb_select_language(callback: CallbackQuery, state: FSMContext):
    """Handle language toggle"""
    lang_action = callback.data.split(":")[-1]
    data = await state.get_data()
    selected = data.get("target_languages", [])
    
    if lang_action == "all":
        # Clear selection = all languages
        selected = []
    elif lang_action == "done":
        # Proceed to content
        if not selected:
            selected = LANGUAGES.copy()  # All languages
        
        await state.update_data(target_languages=selected, current_content_lang=selected[0])
        
        target_bot = data.get("target_bot", "?")
        target_audience = data.get("target_audience", "?")
        
        await safe_edit_text(callback,
            "◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            "     📢 <b>НОВАЯ РАССЫЛКА</b>\n"
            "◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"🤖 Бот: <b>{TARGET_BOTS.get(target_bot, target_bot)}</b>\n"
            f"🎯 Аудитория: <b>{AUDIENCES.get(target_audience, target_audience)}</b>\n"
            f"🌐 Языки: <b>{', '.join(selected)}</b>\n\n"
            f"📝 <b>Шаг 4/6:</b> Введите текст для {LANGUAGE_FLAGS.get(selected[0], '🌐')} <b>{selected[0].upper()}</b>:\n\n"
            "<i>Поддерживается HTML форматирование.\n"
            "Переменные: {name} — имя пользователя</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=get_content_keyboard(selected, selected[0], {})
        )
        await state.set_state(BroadcastStates.enter_content)
        await callback.answer()
        return
    else:
        # Toggle language
        if lang_action in selected:
            selected.remove(lang_action)
        else:
            selected.append(lang_action)
    
    await state.update_data(target_languages=selected)
    await callback.message.edit_reply_markup(reply_markup=get_languages_keyboard(selected))
    await callback.answer()


# ==================== CONTENT INPUT ====================

@router.message(BroadcastStates.enter_content, F.text)
async def msg_content_input(message: Message, state: FSMContext):
    """Handle content text input"""
    data = await state.get_data()
    current_lang = data.get("current_content_lang")
    target_languages = data.get("target_languages", [])
    content = data.get("content", {})
    
    # Save content for current language
    content[current_lang] = {
        "text": message.text,
        "parse_mode": "HTML"
    }
    
    # Check which languages are filled
    filled = {lang: lang in content for lang in target_languages}
    
    # Find next unfilled language
    next_lang = None
    for lang in target_languages:
        if lang not in content:
            next_lang = lang
            break
    
    await state.update_data(content=content)
    
    if next_lang:
        # Move to next language
        await state.update_data(current_content_lang=next_lang)
        
        await message.answer(
            f"✅ Контент для {LANGUAGE_FLAGS.get(current_lang, '🌐')} {current_lang.upper()} сохранён!\n\n"
            f"📝 Теперь введите текст для {LANGUAGE_FLAGS.get(next_lang, '🌐')} <b>{next_lang.upper()}</b>:\n\n"
            "<i>Или нажмите кнопку языка для редактирования</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=get_content_keyboard(target_languages, next_lang, filled)
        )
    else:
        # All languages filled
        await message.answer(
            f"✅ Контент для {LANGUAGE_FLAGS.get(current_lang, '🌐')} {current_lang.upper()} сохранён!\n\n"
            "✨ <b>Все языки заполнены!</b>\n\n"
            "Нажмите ✅ Готово для продолжения или выберите язык для редактирования.",
            parse_mode=ParseMode.HTML,
            reply_markup=get_content_keyboard(target_languages, current_lang, filled)
        )


@router.callback_query(BroadcastStates.enter_content, F.data.startswith("bc:content:"))
async def cb_content_action(callback: CallbackQuery, state: FSMContext):
    """Handle content navigation"""
    action = callback.data.split(":")[-1]
    data = await state.get_data()
    target_languages = data.get("target_languages", [])
    content = data.get("content", {})
    filled = {lang: lang in content for lang in target_languages}
    
    if action == "done":
        # All content entered, move to media
        await safe_edit_text(callback,
            "◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            "     📢 <b>НОВАЯ РАССЫЛКА</b>\n"
            "◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            "📷 <b>Шаг 5/6:</b> Загрузите медиа (фото/видео)\n\n"
            "<i>Или нажмите \"Пропустить\" для текстовой рассылки</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=get_media_keyboard()
        )
        await state.set_state(BroadcastStates.upload_media)
        await callback.answer()
    elif action in LANGUAGES:
        # Switch to editing this language
        await state.update_data(current_content_lang=action)
        
        existing = content.get(action, {}).get("text", "")
        hint = f"\n\n<i>Текущий текст:\n<code>{existing[:200]}...</code></i>" if existing else ""
        
        await safe_edit_text(callback,
            f"📝 Введите текст для {LANGUAGE_FLAGS.get(action, '🌐')} <b>{action.upper()}</b>:{hint}",
            parse_mode=ParseMode.HTML,
            reply_markup=get_content_keyboard(target_languages, action, filled)
        )
        await callback.answer()


# ==================== MEDIA UPLOAD ====================

@router.message(BroadcastStates.upload_media, F.photo)
async def msg_media_photo(message: Message, state: FSMContext):
    """Handle photo upload"""
    file_id = message.photo[-1].file_id
    
    await state.update_data(media_type="photo", media_file_id=file_id)
    
    await message.answer(
        "✅ Фото загружено!\n\n"
        "🔘 <b>Шаг 6/6:</b> Добавить кнопки?\n\n"
        "<i>Формат: <code>Текст RU | Текст EN | URL</code></i>",
        parse_mode=ParseMode.HTML,
        reply_markup=get_buttons_keyboard(False)
    )
    await state.set_state(BroadcastStates.add_buttons)


@router.message(BroadcastStates.upload_media, F.video)
async def msg_media_video(message: Message, state: FSMContext):
    """Handle video upload"""
    file_id = message.video.file_id
    
    await state.update_data(media_type="video", media_file_id=file_id)
    
    await message.answer(
        "✅ Видео загружено!\n\n"
        "🔘 <b>Шаг 6/6:</b> Добавить кнопки?\n\n"
        "<i>Формат: <code>Текст RU | Текст EN | URL</code></i>",
        parse_mode=ParseMode.HTML,
        reply_markup=get_buttons_keyboard(False)
    )
    await state.set_state(BroadcastStates.add_buttons)


@router.callback_query(BroadcastStates.upload_media, F.data == "bc:media:skip")
async def cb_skip_media(callback: CallbackQuery, state: FSMContext):
    """Skip media upload"""
    await safe_edit_text(callback,
        "🔘 <b>Шаг 6/6:</b> Добавить кнопки?\n\n"
        "<i>Формат: <code>Текст RU | Текст EN | URL</code></i>",
        parse_mode=ParseMode.HTML,
        reply_markup=get_buttons_keyboard(False)
    )
    await state.set_state(BroadcastStates.add_buttons)
    await callback.answer()


# ==================== BUTTONS ====================

@router.message(BroadcastStates.add_buttons, F.text)
async def msg_button_input(message: Message, state: FSMContext):
    """Handle button input"""
    # Parse: "Text RU | Text EN | URL"
    parts = [p.strip() for p in message.text.split("|")]
    
    if len(parts) < 2:
        await message.answer(
            "⚠️ Неверный формат!\n\n"
            "Используйте: <code>Текст RU | Текст EN | URL</code>\n"
            "Или: <code>Текст | URL</code> (для всех языков)",
            parse_mode=ParseMode.HTML
        )
        return
    
    data = await state.get_data()
    
    # Validate that we have required data
    if not data.get("target_bot") or not data.get("target_audience"):
        await message.answer(
            "⚠️ Данные рассылки потеряны.\n\n"
            "Начните заново: /broadcast",
            parse_mode=ParseMode.HTML
        )
        await state.clear()
        return
    
    buttons = data.get("buttons", [])
    
    if len(parts) == 2:
        # Same text for all languages
        text_all, url = parts
        button = {
            "text": {lang: text_all for lang in data.get("target_languages", ["ru", "en"])},
            "url": url
        }
    else:
        # Localized text
        text_ru, text_en, url = parts[0], parts[1], parts[2]
        button = {
            "text": {"ru": text_ru, "en": text_en},
            "url": url
        }
    
    buttons.append(button)
    await state.update_data(buttons=buttons)
    
    await message.answer(
        f"✅ Кнопка добавлена! (всего: {len(buttons)})\n\n"
        "Добавить ещё или продолжить?",
        reply_markup=get_buttons_keyboard(True)
    )


@router.callback_query(BroadcastStates.add_buttons, F.data.in_(["bc:btn:skip", "bc:btn:done"]))
async def cb_buttons_done(callback: CallbackQuery, state: FSMContext):
    """Finish buttons step"""
    data = await state.get_data()
    
    # Debug: log state data
    logger.debug(f"cb_buttons_done: state data keys = {list(data.keys())}")
    logger.debug(f"cb_buttons_done: target_bot = {data.get('target_bot')}, target_audience = {data.get('target_audience')}")
    
    # Validate required fields
    target_bot = data.get("target_bot")
    target_audience = data.get("target_audience")
    
    if not target_bot or not target_audience:
        # Try to restore from callback data or provide better error message
        logger.warning(f"Missing broadcast data in state. Available keys: {list(data.keys())}")
        await callback.answer(
            "⚠️ Данные рассылки потеряны.\n\n"
            "Возможные причины:\n"
            "• Слишком долгая пауза между шагами\n"
            "• Перезапуск сервера\n\n"
            "Начните рассылку заново: /broadcast",
            show_alert=True
        )
        await state.clear()
        return
    
    # Count recipients
    db = get_database()
    recipients = await _count_recipients(db, target_bot, target_audience, data.get("target_languages"))
    
    await state.update_data(total_recipients=recipients)
    
    bot_name = TARGET_BOTS.get(target_bot, "?")
    aud_name = AUDIENCES.get(target_audience, "?")
    langs = ", ".join(data.get("target_languages", [])) or "Все"
    media = data.get("media_type", "Нет")
    buttons_count = len(data.get("buttons", []))
    
    await safe_edit_text(callback,
        "◈━━━━━━━━━━━━━━━━━━━━━◈\n"
        "     📋 <b>ПРЕВЬЮ РАССЫЛКИ</b>\n"
        "◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
        f"🤖 <b>Бот:</b> {bot_name}\n"
        f"🎯 <b>Аудитория:</b> {aud_name}\n"
        f"🌐 <b>Языки:</b> {langs}\n"
        f"📷 <b>Медиа:</b> {media}\n"
        f"🔘 <b>Кнопок:</b> {buttons_count}\n"
        f"👥 <b>Получателей:</b> ~{recipients:,}\n\n"
        "Выберите действие:",
        parse_mode=ParseMode.HTML,
        reply_markup=get_preview_keyboard()
    )
    await state.set_state(BroadcastStates.preview)
    await callback.answer()


# ==================== PREVIEW & SEND ====================

@router.callback_query(BroadcastStates.preview, F.data.startswith("bc:preview:"))
async def cb_preview_language(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Show preview for specific language"""
    lang = callback.data.split(":")[-1]
    data = await state.get_data()
    
    content = data.get("content", {})
    msg_data = content.get(lang) or content.get("en") or list(content.values())[0]
    text = msg_data.get("text", "")
    
    # Build keyboard
    keyboard = _build_keyboard(data.get("buttons", []), lang)
    
    # Send preview
    media_file_id = data.get("media_file_id")
    media_type = data.get("media_type")
    
    try:
        if media_file_id and media_type == "photo":
            await bot.send_photo(
                chat_id=callback.from_user.id,
                photo=media_file_id,
                caption=f"👁 <b>ПРЕВЬЮ ({lang.upper()}):</b>\n\n{text}",
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
        elif media_file_id and media_type == "video":
            await bot.send_video(
                chat_id=callback.from_user.id,
                video=media_file_id,
                caption=f"👁 <b>ПРЕВЬЮ ({lang.upper()}):</b>\n\n{text}",
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
        else:
            await bot.send_message(
                chat_id=callback.from_user.id,
                text=f"👁 <b>ПРЕВЬЮ ({lang.upper()}):</b>\n\n{text}",
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
        await callback.answer()
    except Exception as e:
        await callback.answer(f"Ошибка превью: {e}", show_alert=True)


@router.callback_query(BroadcastStates.preview, F.data == "bc:send:now")
async def cb_send_now(callback: CallbackQuery, state: FSMContext, admin_id: str):
    """Send broadcast immediately"""
    data = await state.get_data()
    
    # Validate required fields
    target_bot = data.get("target_bot")
    target_audience = data.get("target_audience")
    
    if not target_bot or not target_audience:
        await callback.answer("Ошибка: данные рассылки не найдены. Начните заново.", show_alert=True)
        await state.clear()
        return
    
    db = get_database()
    
    # Create broadcast record
    broadcast_data = {
        "target_bot": target_bot,
        "content": data.get("content", {}),
        "media_type": data.get("media_type"),
        "media_file_id": data.get("media_file_id"),
        "buttons": data.get("buttons", []),
        "target_audience": target_audience,
        "target_languages": data.get("target_languages"),
        "status": "sending",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "total_recipients": data.get("total_recipients", 0),
        "created_by": admin_id
    }
    
    result = db.client.table("broadcast_messages").insert(broadcast_data).execute()
    broadcast_id = result.data[0]["id"]
    
    await state.clear()
    
    await safe_edit_text(callback,
        "◈━━━━━━━━━━━━━━━━━━━━━◈\n"
        "     🚀 <b>РАССЫЛКА ЗАПУЩЕНА</b>\n"
        "◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
        f"📊 ID: <code>{broadcast_id[:8]}</code>\n"
        f"👥 Получателей: ~{data.get('total_recipients', 0):,}\n\n"
        "<i>Рассылка обрабатывается в фоне.\n"
        "Используйте /broadcasts для отслеживания.</i>",
        parse_mode=ParseMode.HTML
    )
    
    # Queue broadcast worker via QStash (would be implemented in workers.py)
    # For now, log the action
    logger.info(f"Broadcast {broadcast_id} queued for sending")
    
    await callback.answer("🚀 Рассылка запущена!")


# ==================== NAVIGATION ====================

@router.callback_query(F.data == "bc:cancel")
async def cb_cancel(callback: CallbackQuery, state: FSMContext):
    """Cancel broadcast creation"""
    await state.clear()
    await safe_edit_text(callback,"❌ Рассылка отменена.")
    await callback.answer()


@router.callback_query(F.data.startswith("bc:back:"))
async def cb_back(callback: CallbackQuery, state: FSMContext):
    """Handle back navigation"""
    target = callback.data.split(":")[-1]
    data = await state.get_data()
    
    if target == "bot":
        await safe_edit_text(callback,
            "◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            "     📢 <b>НОВАЯ РАССЫЛКА</b>\n"
            "◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            "🤖 <b>Шаг 1/6:</b> Выберите бота для рассылки:",
            parse_mode=ParseMode.HTML,
            reply_markup=get_bot_keyboard()
        )
        await state.set_state(BroadcastStates.select_bot)
    
    elif target == "audience":
        await safe_edit_text(callback,
            "◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            "     📢 <b>НОВАЯ РАССЫЛКА</b>\n"
            "◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"🤖 Бот: <b>{TARGET_BOTS.get(data.get('target_bot'), '?')}</b>\n\n"
            "🎯 <b>Шаг 2/6:</b> Выберите аудиторию:",
            parse_mode=ParseMode.HTML,
            reply_markup=get_audience_keyboard()
        )
        await state.set_state(BroadcastStates.select_audience)
    
    elif target == "languages":
        await safe_edit_text(callback,
            "◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            "     📢 <b>НОВАЯ РАССЫЛКА</b>\n"
            "◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"🤖 Бот: <b>{TARGET_BOTS.get(data.get('target_bot'), '?')}</b>\n"
            f"🎯 Аудитория: <b>{AUDIENCES.get(data.get('target_audience'), '?')}</b>\n\n"
            "🌐 <b>Шаг 3/6:</b> Выберите языки:",
            parse_mode=ParseMode.HTML,
            reply_markup=get_languages_keyboard(data.get("target_languages", []))
        )
        await state.set_state(BroadcastStates.select_languages)
    
    elif target == "content":
        target_languages = data.get("target_languages", [])
        content = data.get("content", {})
        filled = {lang: lang in content for lang in target_languages}
        current = target_languages[0] if target_languages else "ru"
        
        await safe_edit_text(callback,
            f"📝 <b>Шаг 4/6:</b> Введите текст для {LANGUAGE_FLAGS.get(current, '🌐')} <b>{current.upper()}</b>:",
            parse_mode=ParseMode.HTML,
            reply_markup=get_content_keyboard(target_languages, current, filled)
        )
        await state.set_state(BroadcastStates.enter_content)
    
    elif target == "media":
        await safe_edit_text(callback,
            "📷 <b>Шаг 5/6:</b> Загрузите медиа (фото/видео)\n\n"
            "<i>Или нажмите \"Пропустить\" для текстовой рассылки</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=get_media_keyboard()
        )
        await state.set_state(BroadcastStates.upload_media)
    
    elif target == "buttons":
        await safe_edit_text(callback,
            "🔘 <b>Шаг 6/6:</b> Добавить кнопки?\n\n"
            "<i>Формат: <code>Текст RU | Текст EN | URL</code></i>",
            parse_mode=ParseMode.HTML,
            reply_markup=get_buttons_keyboard(bool(data.get("buttons")))
        )
        await state.set_state(BroadcastStates.add_buttons)
    
    await callback.answer()


# ==================== HELPER FUNCTIONS ====================

async def _count_recipients(db, target_bot: str, audience: str, languages: Optional[List[str]]) -> int:
    """Count recipients based on targeting criteria"""
    from datetime import timedelta
    
    query = db.client.table("users").select("id", count="exact")
    
    # Base filters
    query = query.eq("is_banned", False).eq("do_not_disturb", False)
    
    # Bot-specific filter
    if target_bot == "discount":
        query = query.eq("discount_tier_source", True)
    
    # Audience filter
    now = datetime.now(timezone.utc)
    if audience == "active":
        query = query.gte("last_activity_at", (now - timedelta(days=7)).isoformat())
    elif audience == "inactive":
        query = query.lt("last_activity_at", (now - timedelta(days=7)).isoformat())
    elif audience == "vip":
        query = query.eq("is_partner", True)
    
    # Language filter
    if languages:
        query = query.in_("language_code", languages)
    
    result = query.execute()
    return result.count or 0


def _build_keyboard(buttons: List[Dict], lang: str) -> Optional[InlineKeyboardMarkup]:
    """Build localized keyboard from button config"""
    if not buttons:
        return None
    
    from aiogram.types import WebAppInfo
    
    rows = []
    for btn in buttons:
        text_dict = btn.get("text", {})
        text = text_dict.get(lang) or text_dict.get("en") or list(text_dict.values())[0] if text_dict else "Button"
        
        if "url" in btn:
            rows.append([InlineKeyboardButton(text=text, url=btn["url"])])
        elif "web_app" in btn:
            rows.append([InlineKeyboardButton(text=text, web_app=WebAppInfo(url=btn["web_app"]["url"]))])
        elif "callback_data" in btn:
            rows.append([InlineKeyboardButton(text=text, callback_data=btn["callback_data"])])
    
    return InlineKeyboardMarkup(inline_keyboard=rows) if rows else None
