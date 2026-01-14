"""
NotificationService Base Module

Core class and helpers for all notification types.
Integrates with telegram_messaging.py for unified message sending.
All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""

from core.logging import get_logger
from core.services.database import get_database

logger = get_logger(__name__)


async def get_user_language(telegram_id: int) -> str:
    """Get user's preferred language from database."""
    try:
        from core.i18n import detect_language

        db = get_database()
        result = (
            await db.client.table("users")
            .select("interface_language, language_code")
            .eq("telegram_id", telegram_id)
            .limit(1)
            .execute()
        )
        if result.data:
            # Prefer interface_language, fallback to language_code
            lang = (
                result.data[0].get("interface_language")
                or result.data[0].get("language_code")
                or "en"
            )
            # Normalize using detect_language to support all languages
            return detect_language(lang)
    except Exception as e:
        logger.warning(f"Failed to get user language for {telegram_id}: {e}")
    return "en"


def _msg(lang: str, ru: str, en: str) -> str:
    """Return message in user's language."""
    return ru if lang == "ru" else en


async def get_referral_settings() -> dict:
    """Get referral program settings from database."""
    try:
        db = get_database()
        result = await db.client.table("referral_settings").select("*").limit(1).execute()
        if result.data:
            s = result.data[0]
            return {
                "level1_percent": int(s.get("level1_commission_percent", 10) or 10),
                "level2_percent": int(s.get("level2_commission_percent", 7) or 7),
                "level3_percent": int(s.get("level3_commission_percent", 3) or 3),
                "level2_threshold": int(s.get("level2_threshold_usd", 250) or 250),
                "level3_threshold": int(s.get("level3_threshold_usd", 1000) or 1000),
            }
    except Exception as e:
        logger.warning(f"Failed to get referral settings: {e}")
    # Default values
    return {
        "level1_percent": 10,
        "level2_percent": 7,
        "level3_percent": 3,
        "level2_threshold": 250,
        "level3_threshold": 1000,
    }


class NotificationServiceBase:
    """Base class for NotificationService.

    All notification methods use telegram_messaging.py for unified message sending.
    No direct bot access needed.
    """

    def __init__(self):
        # Base class initialization - subclasses may extend this
        # No state needed at base level as we use external services
        pass
