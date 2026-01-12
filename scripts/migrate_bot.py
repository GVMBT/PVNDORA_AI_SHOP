#!/usr/bin/env python3
"""
Bot Migration Script

Use this script to migrate to a backup bot if the main bot is banned.
Updates webhook and notifies users via channel.

Usage:
    python scripts/migrate_bot.py --new-token "NEW_BOT_TOKEN" --channel "@pvndora_news"
"""
import argparse
import asyncio
import os
import sys

import httpx

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def set_webhook(token: str, webhook_url: str) -> bool:
    """Set webhook for a bot."""
    url = f"https://api.telegram.org/bot{token}/setWebhook"
    payload = {
        "url": webhook_url,
        "allowed_updates": ["message", "callback_query"],
        "drop_pending_updates": True,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, timeout=10)
        result = response.json()
        return result.get("ok", False)


async def send_channel_message(token: str, channel: str, text: str) -> bool:
    """Send message to a channel."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": channel, "text": text, "parse_mode": "HTML"}

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, timeout=10)
        result = response.json()
        return result.get("ok", False)


async def get_bot_info(token: str) -> dict:
    """Get bot info."""
    url = f"https://api.telegram.org/bot{token}/getMe"

    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=10)
        result = response.json()
        if result.get("ok"):
            return result["result"]
    return {}


async def migrate_bot(new_token: str, webhook_url: str, channel: str, is_discount: bool = False):
    """Perform bot migration."""
    print("Starting bot migration...")

    # 1. Get new bot info
    print("Getting new bot info...")
    bot_info = await get_bot_info(new_token)
    if not bot_info:
        print("ERROR: Could not get bot info. Check token.")
        return False

    new_username = bot_info.get("username", "unknown")
    print(f"New bot: @{new_username}")

    # 2. Set webhook
    print(f"Setting webhook to: {webhook_url}")
    if await set_webhook(new_token, webhook_url):
        print("Webhook set successfully!")
    else:
        print("ERROR: Failed to set webhook")
        return False

    # 3. Send announcement to channel
    if channel:
        bot_type = "дискаунт-бот" if is_discount else "PVNDORA"
        text = (
            f"⚠️ <b>Важное обновление!</b>\n\n"
            f"Наш {bot_type} переехал!\n\n"
            f"Новый адрес: @{new_username}\n\n"
            f"Все ваши заказы и данные сохранены.\n"
            f"Просто перейдите к новому боту и нажмите /start"
        )

        print(f"Sending announcement to {channel}...")
        if await send_channel_message(new_token, channel, text):
            print("Announcement sent!")
        else:
            print("WARNING: Failed to send announcement")

    # 4. Instructions for Vercel
    print("\n" + "=" * 50)
    print("NEXT STEPS:")
    print("=" * 50)

    if is_discount:
        print("1. Update DISCOUNT_BOT_TOKEN in Vercel:")
        print("   vercel env add DISCOUNT_BOT_TOKEN --production")
        print(f"   Value: {new_token[:20]}...")
    else:
        print("1. Update TELEGRAM_TOKEN in Vercel:")
        print("   vercel env add TELEGRAM_TOKEN --production")
        print(f"   Value: {new_token[:20]}...")

    print("\n2. Redeploy the project:")
    print("   vercel --prod")

    print("\n3. Verify webhook:")
    print(f"   curl https://api.telegram.org/bot{new_token[:20]}...]/getWebhookInfo")

    print("\n" + "=" * 50)
    print("Migration complete!")
    return True


async def main():
    parser = argparse.ArgumentParser(description="Migrate Telegram bot to backup")
    parser.add_argument("--new-token", required=True, help="New bot token from BotFather")
    parser.add_argument(
        "--webhook-url", default=None, help="Webhook URL (defaults to WEBAPP_URL/webhook/telegram)"
    )
    parser.add_argument("--channel", default="@pvndora_news", help="Channel to announce migration")
    parser.add_argument(
        "--discount", action="store_true", help="Migrate discount bot instead of main"
    )

    args = parser.parse_args()

    # Determine webhook URL
    webapp_url = os.environ.get("WEBAPP_URL", "https://pvndora.app")
    if args.webhook_url:
        webhook_url = args.webhook_url
    elif args.discount:
        webhook_url = f"{webapp_url}/webhook/discount"
    else:
        webhook_url = f"{webapp_url}/webhook/telegram"

    await migrate_bot(
        new_token=args.new_token,
        webhook_url=webhook_url,
        channel=args.channel,
        is_discount=args.discount,
    )


if __name__ == "__main__":
    asyncio.run(main())
