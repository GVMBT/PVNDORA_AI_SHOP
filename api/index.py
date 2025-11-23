from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.types import WebAppInfo
import os
import json
from supabase import create_client, Client
import google.generativeai as genai

# Load environment variables (Vercel will provide these)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Initialize Apps
app = FastAPI()
bot = Bot(token=TELEGRAM_TOKEN) if TELEGRAM_TOKEN else None
dp = Dispatcher()
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL else None

# Configure Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash-exp')

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "AI-Shop-Platform"}

@app.post("/api/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        update = types.Update(**data)
        await dp.feed_update(bot, update)
        return {"status": "ok"}
    except Exception as e:
        print(f"Error: {e}")
        return {"status": "error", "message": str(e)}

# --- AI Logic Placeholders ---
async def get_dynamic_system_prompt(user_id: int):
    """Fetches available products and constructs the system prompt."""
    # TODO: Fetch from Supabase: 
    # products = supabase.table('products').select('*').execute()
    # waitlist = supabase.table('waitlist').select('*').eq('user_id', user_id).execute()
    
    # Mock Data
    products = [
        {"name": "ChatGPT Plus", "price": 250, "stock": 5, "status": "active", "instructions": "Files supported."},
        {"name": "Claude Pro", "price": 300, "stock": 0, "status": "out_of_stock", "instructions": "Best for coding."},
        {"name": "11Labs Vol 1", "price": 0, "stock": 0, "status": "discontinued", "reason": "Waiting for Vol 2"}
    ]
    
    inventory_text = "CURRENT INVENTORY:\n"
    for p in products:
        if p['status'] == 'active' and p['stock'] > 0:
            inventory_text += f"- {p['name']}: {p['price']} RUB. {p['instructions']}\n"
        elif p['status'] == 'out_of_stock':
            inventory_text += f"- {p['name']}: OUT OF STOCK. (Offer Waitlist)\n"
        elif p['status'] == 'discontinued':
            inventory_text += f"- {p['name']}: DISCONTINUED. Reason: {p.get('reason')}. (Offer Waitlist for alternative)\n"
            
    return f"""You are an AI Sales Consultant for a Digital Marketplace.
    
    {inventory_text}
    
    RULES:
    1. Only sell what is ACTIVE and IN STOCK.
    2. If OUT OF STOCK or DISCONTINUED, explain why and offer to add to WAITLIST.
    3. If user asks for support/replacement, tell them to use the 'Problem' button in their order history (or type /support).
    4. Be concise.
    """

async def add_to_waitlist(user_id: int, product_name: str):
    # supabase.table('waitlist').insert({'user_id': user_id, 'product_name': product_name}).execute()
    return True

# --- Bot Handlers (to be moved to bot/handlers.py later) ---
@dp.message()
async def handle_message(message: types.Message):
    # 1. Check if Banned
    # user = supabase.table('users').select('is_banned').eq('telegram_id', message.from_user.id).execute()
    # if user.data and user.data[0]['is_banned']:
    #     await message.answer("Access restricted. Appeal: @admin")
    #     return

    # 2. Get System Prompt
    system_prompt = await get_dynamic_system_prompt(message.from_user.id)
    
    # 3. Call Gemini (Mock)
    # response = model.generate_content([system_prompt, message.text])
    # reply = response.text
    
    reply = f"[AI Mock] I see you want {message.text}. Based on inventory: ..."
    
    await message.answer(reply)
