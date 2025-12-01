"""
Diagnose webhook issues
Usage: python scripts/diagnose_webhook.py
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
        print(f"📄 Loaded .env from {env_path}\n")
except ImportError:
    pass

async def diagnose():
    """Diagnose webhook configuration"""
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        print("❌ TELEGRAM_TOKEN not set")
        return
    
    webhook_url = os.environ.get("TELEGRAM_WEBHOOK_URL", "https://pvndora.app/webhook/telegram")
    base_url = f"https://api.telegram.org/bot{token}"
    
    print("🔍 Диагностика webhook...\n")
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        # 1. Check bot info
        print("1️⃣ Проверка бота...")
        try:
            response = await client.get(f"{base_url}/getMe")
            result = response.json()
            if result.get("ok"):
                bot = result["result"]
                print(f"   ✅ Бот: @{bot.get('username')} ({bot.get('first_name')})")
            else:
                print(f"   ❌ Ошибка: {result.get('description')}")
                return
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
            return
        
        # 2. Check webhook info
        print(f"\n2️⃣ Проверка webhook...")
        try:
            response = await client.get(f"{base_url}/getWebhookInfo")
            result = response.json()
            if result.get("ok"):
                info = result["result"]
                current_url = info.get("url", "")
                pending = info.get("pending_update_count", 0)
                last_error = info.get("last_error_date")
                last_error_msg = info.get("last_error_message", "")
                
                print(f"   Текущий URL: {current_url}")
                print(f"   Ожидающих обновлений: {pending}")
                
                if current_url != webhook_url:
                    print(f"   ⚠️  URL не совпадает!")
                    print(f"   Ожидается: {webhook_url}")
                    print(f"   Текущий: {current_url}")
                else:
                    print(f"   ✅ URL совпадает")
                
                if last_error:
                    print(f"   ⚠️  Последняя ошибка ({last_error}): {last_error_msg}")
                else:
                    print(f"   ✅ Ошибок нет")
            else:
                print(f"   ❌ Ошибка: {result.get('description')}")
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
        
        # 3. Test webhook endpoint
        print(f"\n3️⃣ Тест webhook endpoint...")
        try:
            test_payload = {
                "update_id": 999999999,
                "message": {
                    "message_id": 1,
                    "date": 1234567890,
                    "chat": {"id": 123456789, "type": "private"},
                    "from": {"id": 123456789, "is_bot": False, "first_name": "Test"},
                    "text": "/start"
                }
            }
            
            response = await client.post(
                webhook_url,
                json=test_payload,
                headers={"Content-Type": "application/json"},
                follow_redirects=True
            )
            
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print(f"   ✅ Endpoint доступен")
                result = response.json()
                if result.get("error"):
                    print(f"   ⚠️  Ответ: {result.get('error')}")
            else:
                print(f"   ❌ Endpoint недоступен: {response.text}")
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
        
        # 4. Recommendations
        print(f"\n📋 Рекомендации:")
        if current_url != webhook_url:
            print(f"   1. Обновите webhook: python scripts/set_webhook.py")
        if last_error:
            print(f"   2. Проверьте логи Vercel для деталей ошибки")
        if pending > 0:
            print(f"   3. Есть {pending} ожидающих обновлений - возможно, webhook не обрабатывает их")

if __name__ == "__main__":
    asyncio.run(diagnose())


