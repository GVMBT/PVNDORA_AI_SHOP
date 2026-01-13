"""
Re-engagement Cron Job
Schedule: 0 12 * * * (12:00 PM UTC daily)

Tasks:
1. Send notifications to users who haven't been active for 7+ days
2. Remind about items in wishlist
3. Notify about expiring subscriptions
"""

import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

# Add project root to path for imports BEFORE any core.* imports
_base_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_base_path))
if str(_base_path) not in sys.path:
    sys.path.insert(0, str(_base_path.resolve()))

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from core.logging import get_logger

logger = get_logger(__name__)

CRON_SECRET = os.environ.get("CRON_SECRET", "")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
BOT_USERNAME = "pvndora_ai_bot"

app = FastAPI()


async def _send_telegram_message(telegram_id: int | str, message: str) -> bool:
    """Send a message via Telegram Bot API."""
    import httpx

    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json={"chat_id": telegram_id, "text": message, "parse_mode": "HTML"},
                timeout=10,
            )
        return True
    except Exception as e:
        logger.error(f"Failed to send to {telegram_id}: {e}", exc_info=True)
        return False


async def _process_inactive_users(db: Any, now: datetime) -> int:
    """Send re-engagement messages to inactive users."""
    from core.i18n import get_text

    inactive_cutoff = now - timedelta(days=7)
    max_inactive = now - timedelta(days=14)
    reengagement_cutoff = now - timedelta(days=3)

    inactive_users = (
        await db.client.table("users")
        .select("id,telegram_id,language_code,first_name,last_reengagement_at")
        .lt("last_activity_at", inactive_cutoff.isoformat())
        .gt("last_activity_at", max_inactive.isoformat())
        .eq("do_not_disturb", False)
        .eq("is_banned", False)
        .limit(50)
        .execute()
    )

    sent_count = 0
    for user_raw in inactive_users.data or []:
        if not isinstance(user_raw, dict):
            continue
        user = cast(dict[str, Any], user_raw)

        # Skip if recently contacted
        if _was_recently_contacted(user.get("last_reengagement_at"), reengagement_cutoff):
            continue

        lang = user.get("language_code", "en")
        name = user.get("first_name", "")
        message = get_text("reengagement_message", lang, name=name)

        if await _send_telegram_message(user["telegram_id"], message):
            await (
                db.client.table("users")
                .update({"last_reengagement_at": now.isoformat()})
                .eq("id", user["id"])
                .execute()
            )
            sent_count += 1

    return sent_count


def _was_recently_contacted(last_reengagement: str | None, cutoff: datetime) -> bool:
    """Check if user was contacted within the cutoff period."""
    if not last_reengagement:
        return False
    try:
        last_dt = datetime.fromisoformat(last_reengagement.replace("Z", "+00:00"))
        return last_dt > cutoff
    except (ValueError, AttributeError):
        return False


async def _process_wishlist_reminders(db: Any, now: datetime) -> int:
    """Send reminders for old wishlist items."""
    from core.i18n import get_text

    wishlist_cutoff = now - timedelta(days=3)
    wishlist_items = (
        await db.client.table("wishlist")
        .select("id,user_id,product_name,users(telegram_id,language_code)")
        .eq("reminded", False)
        .lt("created_at", wishlist_cutoff.isoformat())
        .limit(50)
        .execute()
    )

    wishlist_sent = 0
    for item_raw in wishlist_items.data or []:
        if not isinstance(item_raw, dict):
            continue
        item = cast(dict[str, Any], item_raw)
        user_data = item.get("users")
        if not isinstance(user_data, dict):
            continue

        lang = user_data.get("language_code", "en")
        message = get_text("wishlist_reminder", lang, product=item.get("product_name", ""))

        if await _send_telegram_message(user_data["telegram_id"], message):
            await (
                db.client.table("wishlist")
                .update({"reminded": True})
                .eq("id", item["id"])
                .execute()
            )
            wishlist_sent += 1

    return wishlist_sent


async def _process_expiring_subscriptions(db: Any, now: datetime) -> int:
    """Notify users about expiring subscriptions."""
    from core.i18n import get_text

    expiry_window_start = now + timedelta(days=2)
    expiry_window_end = now + timedelta(days=4)

    expiring_items = (
        await db.client.table("order_items")
        .select(
            "id,order_id,expires_at,products(name),orders(user_telegram_id,users(language_code))"
        )
        .eq("status", "delivered")
        .gte("expires_at", expiry_window_start.isoformat())
        .lte("expires_at", expiry_window_end.isoformat())
        .limit(50)
        .execute()
    )

    expiry_sent = 0
    notified_users: set[Any] = set()

    for item_raw in expiring_items.data or []:
        if not isinstance(item_raw, dict):
            continue
        item = cast(dict[str, Any], item_raw)

        order_data = item.get("orders")
        product_data = item.get("products")
        if not isinstance(order_data, dict) or not isinstance(product_data, dict):
            continue

        telegram_id = order_data.get("user_telegram_id")
        if not telegram_id or telegram_id in notified_users:
            continue

        days_left = _calculate_days_left(item.get("expires_at"), now)
        user_data = order_data.get("users", {})
        lang = user_data.get("language_code", "en") if isinstance(user_data, dict) else "en"

        message = get_text(
            "subscription_expiring", lang, product=product_data.get("name", ""), days=days_left
        )

        if await _send_telegram_message(telegram_id, message):
            expiry_sent += 1
            notified_users.add(telegram_id)

    return expiry_sent


def _calculate_days_left(expires_at_str: str | None, now: datetime) -> int:
    """Calculate days left until expiry."""
    if not expires_at_str:
        return 3
    try:
        expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
        return (expires_at - now).days
    except (ValueError, AttributeError):
        return 3


@app.get("/api/cron/reengagement")
async def reengagement_entrypoint(request: Request):
    """Vercel Cron entrypoint for re-engagement notifications."""
    auth_header = request.headers.get("Authorization", "")
    if CRON_SECRET and auth_header != f"Bearer {CRON_SECRET}":
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    from core.services.database import get_database_async

    db = await get_database_async()
    now = datetime.now(UTC)
    results: dict[str, Any] = {"timestamp": now.isoformat(), "tasks": {}, "success": True}

    try:
        # 1. Inactive users
        results["tasks"]["reengagement_sent"] = await _process_inactive_users(db, now)

        # 2. Wishlist reminders
        results["tasks"]["wishlist_reminders_sent"] = await _process_wishlist_reminders(db, now)

        # 3. Expiring subscriptions
        results["tasks"]["expiry_notifications_sent"] = await _process_expiring_subscriptions(
            db, now
        )

    except Exception as e:
        results["success"] = False
        results["error"] = str(e)

    return JSONResponse(results)
