"""
Bot Setup Script - Configure bot name, description, commands via Telegram API

Run once after deployment to set up bot info in all languages.
Usage: python scripts/setup_bot.py
"""
import os
import json
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


async def setup_bot():
    """Set up bot with BotFather API"""
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        print("Error: TELEGRAM_TOKEN not set")
        return False
    
    # Load bot info
    info_path = Path(__file__).parent.parent / "bot_setup" / "bot_info.json"
    with open(info_path, "r", encoding="utf-8") as f:
        bot_info = json.load(f)
    
    base_url = f"https://api.telegram.org/bot{token}"
    
    async with httpx.AsyncClient() as client:
        # 1. Set bot commands for each language
        print("Setting bot commands...")
        
        for lang_code in ["en", "ru", "uk", "de", "fr", "es", "tr", "ar", "hi"]:
            commands = []
            for cmd in bot_info["commands"]:
                commands.append({
                    "command": cmd["command"],
                    "description": cmd["description"].get(lang_code, cmd["description"]["en"])
                })
            
            # Set commands for specific language
            response = await client.post(
                f"{base_url}/setMyCommands",
                json={
                    "commands": commands,
                    "language_code": lang_code if lang_code != "en" else ""
                }
            )
            
            if response.json().get("ok"):
                print(f"  ✓ Commands set for {lang_code}")
            else:
                print(f"  ✗ Failed for {lang_code}: {response.json()}")
        
        # 2. Set bot description (shown in chat before starting)
        print("\nSetting bot description...")
        
        for lang_code in ["en", "ru", "uk", "de", "fr", "es", "tr", "ar", "hi"]:
            description = bot_info["description"].get(lang_code, bot_info["description"]["en"])
            
            response = await client.post(
                f"{base_url}/setMyDescription",
                json={
                    "description": description[:512],  # Max 512 chars
                    "language_code": lang_code if lang_code != "en" else ""
                }
            )
            
            if response.json().get("ok"):
                print(f"  ✓ Description set for {lang_code}")
            else:
                print(f"  ✗ Failed for {lang_code}: {response.json()}")
        
        # 3. Set bot short description (shown in profile)
        print("\nSetting short description...")
        
        short_desc = {
            "en": "🤖 AI Consultant for Premium Subscriptions | ChatGPT, Claude, Midjourney",
            "ru": "🤖 AI-Консультант по премиум подпискам | ChatGPT, Claude, Midjourney",
            "uk": "🤖 AI-Консультант з преміум підписок | ChatGPT, Claude, Midjourney",
            "de": "🤖 KI-Berater für Premium-Abos | ChatGPT, Claude, Midjourney",
            "fr": "🤖 Consultant IA pour abonnements premium | ChatGPT, Claude, Midjourney",
            "es": "🤖 Consultor IA para suscripciones premium | ChatGPT, Claude, Midjourney",
            "tr": "🤖 Premium Abonelikler için AI Danışmanı | ChatGPT, Claude, Midjourney",
            "ar": "🤖 مستشار AI للاشتراكات المميزة | ChatGPT, Claude, Midjourney",
            "hi": "🤖 प्रीमियम सब्सक्रिप्शन के लिए AI सलाहकार | ChatGPT, Claude, Midjourney"
        }
        
        for lang_code, desc in short_desc.items():
            response = await client.post(
                f"{base_url}/setMyShortDescription",
                json={
                    "short_description": desc[:120],  # Max 120 chars
                    "language_code": lang_code if lang_code != "en" else ""
                }
            )
            
            if response.json().get("ok"):
                print(f"  ✓ Short description set for {lang_code}")
            else:
                print(f"  ✗ Failed for {lang_code}: {response.json()}")
        
        # 4. Set webhook
        webhook_url = os.environ.get("TELEGRAM_WEBHOOK_URL")
        if webhook_url:
            print(f"\nSetting webhook to: {webhook_url}")
            
            response = await client.post(
                f"{base_url}/setWebhook",
                json={
                    "url": webhook_url,
                    "allowed_updates": ["message", "callback_query", "my_chat_member"],
                    "drop_pending_updates": True
                }
            )
            
            if response.json().get("ok"):
                print("  ✓ Webhook set successfully")
            else:
                print(f"  ✗ Failed: {response.json()}")
        
        # 5. Get bot info
        print("\nBot info:")
        response = await client.get(f"{base_url}/getMe")
        if response.json().get("ok"):
            bot = response.json()["result"]
            print(f"  Name: {bot.get('first_name')}")
            print(f"  Username: @{bot.get('username')}")
            print(f"  ID: {bot.get('id')}")
    
    print("\n✅ Bot setup complete!")
    return True


if __name__ == "__main__":
    asyncio.run(setup_bot())

