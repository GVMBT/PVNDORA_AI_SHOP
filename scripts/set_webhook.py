"""
Simple script to set Telegram webhook
Usage: python scripts/set_webhook.py
"""
import os
import asyncio
import httpx
from pathlib import Path

# Load .env file if exists
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"📄 Loaded .env from {env_path}")
except ImportError:
    # python-dotenv not installed, skip
    pass

async def set_webhook():
    """Set Telegram webhook"""
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        print("❌ Error: TELEGRAM_TOKEN not set")
        print("   Set it in Vercel environment variables or .env file")
        return False
    
    # Get webhook URL from environment or use default
    webhook_url = os.environ.get("TELEGRAM_WEBHOOK_URL")
    if not webhook_url:
        # Default URL based on your project
        # Note: vercel.json has rewrite for /webhook/(.*) -> /api/index.py
        # So the path is /webhook/telegram (NOT /api/webhook/telegram)
        webhook_url = "https://pvndora.app/webhook/telegram"
        print(f"⚠️  TELEGRAM_WEBHOOK_URL not set, using default: {webhook_url}")
    else:
        print(f"📡 Setting webhook to: {webhook_url}")
    
    base_url = f"https://api.telegram.org/bot{token}"
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{base_url}/setWebhook",
            json={
                "url": webhook_url,
                "allowed_updates": ["message", "callback_query", "my_chat_member"],
                "drop_pending_updates": True
            }
        )
        
        result = response.json()
        
        if result.get("ok"):
            print("✅ Webhook установлен успешно!")
            
            # Get webhook info to verify
            info_response = await client.get(f"{base_url}/getWebhookInfo")
            info = info_response.json()
            if info.get("ok"):
                webhook_info = info["result"]
                print("\n📋 Информация о вебхуке:")
                print(f"   URL: {webhook_info.get('url', 'N/A')}")
                print(f"   Ожидает обновлений: {webhook_info.get('pending_update_count', 0)}")
                if webhook_info.get('last_error_date'):
                    print(f"   ⚠️  Последняя ошибка: {webhook_info.get('last_error_message', 'N/A')}")
            return True
        else:
            print(f"❌ Ошибка: {result.get('description', 'Unknown error')}")
            return False

if __name__ == "__main__":
    asyncio.run(set_webhook())







