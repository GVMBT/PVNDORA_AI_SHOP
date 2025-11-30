"""
Script to check Telegram webhook status and diagnose issues
Usage: python scripts/check_webhook.py
"""
import os
import asyncio
import httpx
import json

async def check_webhook():
    """Check webhook status and diagnose issues"""
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        print("❌ Error: TELEGRAM_TOKEN not set")
        return False
    
    webhook_url = os.environ.get("TELEGRAM_WEBHOOK_URL", "https://pvndora.app/api/webhook/telegram")
    base_url = f"https://api.telegram.org/bot{token}"
    
    print("🔍 Проверка вебхука Telegram...\n")
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        # 1. Check bot info
        print("1️⃣ Проверка информации о боте...")
        try:
            response = await client.get(f"{base_url}/getMe")
            result = response.json()
            if result.get("ok"):
                bot = result["result"]
                print(f"   ✅ Бот: @{bot.get('username')} ({bot.get('first_name')})")
            else:
                print(f"   ❌ Ошибка: {result.get('description')}")
                return False
        except Exception as e:
            print(f"   ❌ Ошибка подключения: {e}")
            return False
        
        # 2. Check webhook info
        print("\n2️⃣ Проверка статуса вебхука...")
        try:
            response = await client.get(f"{base_url}/getWebhookInfo")
            result = response.json()
            if result.get("ok"):
                info = result["result"]
                print(f"   URL: {info.get('url', 'N/A')}")
                print(f"   Ожидает обновлений: {info.get('pending_update_count', 0)}")
                
                if info.get('last_error_date'):
                    print(f"   ⚠️  Последняя ошибка ({info.get('last_error_date')}):")
                    print(f"      {info.get('last_error_message', 'N/A')}")
                    print(f"   Количество ошибок: {info.get('max_connections', 'N/A')}")
                
                if info.get('url') != webhook_url:
                    print(f"   ⚠️  URL не совпадает! Ожидается: {webhook_url}")
                else:
                    print("   ✅ URL совпадает")
            else:
                print(f"   ❌ Ошибка: {result.get('description')}")
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
        
        # 3. Test webhook endpoint
        print("\n3️⃣ Проверка доступности эндпоинта вебхука...")
        try:
            # Test with a simple GET request first
            test_url = webhook_url.replace("/webhook/telegram", "/api/webhook/test")
            response = await client.get(test_url, timeout=10.0)
            if response.status_code == 200:
                print(f"   ✅ Эндпоинт доступен (статус: {response.status_code})")
                try:
                    data = response.json()
                    print(f"   Данные: {json.dumps(data, indent=2, ensure_ascii=False)}")
                except Exception:
                    print(f"   Ответ: {response.text[:200]}")
            else:
                print(f"   ⚠️  Эндпоинт вернул статус: {response.status_code}")
                print(f"   Ответ: {response.text[:200]}")
        except httpx.TimeoutException:
            print(f"   ❌ Таймаут при подключении к {webhook_url}")
            print("   Возможно, приложение не задеплоено или недоступно")
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
        
        # 4. Check health endpoint
        print("\n4️⃣ Проверка health check...")
        try:
            health_url = webhook_url.replace("/webhook/telegram", "/api/health")
            response = await client.get(health_url, timeout=10.0)
            if response.status_code == 200:
                print("   ✅ Health check OK")
                print(f"   Ответ: {response.text}")
            else:
                print(f"   ⚠️  Health check вернул: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
        
        # 5. Recommendations
        print("\n📋 Рекомендации:")
        print("   1. Убедитесь, что приложение задеплоено на Vercel")
        print("   2. Проверьте логи Vercel на наличие ошибок")
        print("   3. Убедитесь, что переменные окружения установлены в Vercel")
        print("   4. Попробуйте отправить сообщение боту и проверьте логи")
        print(f"   5. Проверьте вебхук вручную: {base_url}/getWebhookInfo")
    
    return True

if __name__ == "__main__":
    asyncio.run(check_webhook())







