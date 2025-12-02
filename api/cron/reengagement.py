"""
Re-engagement Cron Job
Schedule: 0 12 * * * (12:00 PM UTC daily)

Tasks:
1. Send notifications to users who haven't been active for 7+ days
2. Remind about items in wishlist
3. Notify about expiring subscriptions
"""
from datetime import datetime, timezone, timedelta
from fastapi import Request
from fastapi.responses import JSONResponse
import os
import asyncio

CRON_SECRET = os.environ.get("CRON_SECRET", "")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
BOT_USERNAME = "pvndora_ai_bot"


async def handler(request: Request):
    # Verify the request is from Vercel Cron
    auth_header = request.headers.get("Authorization", "")
    if CRON_SECRET and auth_header != f"Bearer {CRON_SECRET}":
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    from src.services.database import get_database
    from src.i18n import get_text
    import httpx
    
    db = get_database()
    now = datetime.now(timezone.utc)
    results = {
        "timestamp": now.isoformat(),
        "tasks": {}
    }
    
    try:
        # 1. Find inactive users (7-14 days, not contacted recently)
        inactive_cutoff = now - timedelta(days=7)
        max_inactive = now - timedelta(days=14)
        reengagement_cutoff = now - timedelta(days=3)  # Don't spam
        
        inactive_users = db.client.table("users").select(
            "id,telegram_id,language_code,first_name,last_reengagement_at"
        ).lt("last_activity_at", inactive_cutoff.isoformat()).gt(
            "last_activity_at", max_inactive.isoformat()
        ).eq("do_not_disturb", False).eq("is_banned", False).limit(50).execute()
        
        sent_count = 0
        for user in (inactive_users.data or []):
            # Skip if recently contacted
            last_reengagement = user.get("last_reengagement_at")
            if last_reengagement:
                try:
                    last_dt = datetime.fromisoformat(last_reengagement.replace("Z", "+00:00"))
                    if last_dt > reengagement_cutoff:
                        continue
                except:
                    pass
            
            lang = user.get("language_code", "en")
            name = user.get("first_name", "")
            
            # Send re-engagement message
            message = get_text("reengagement_message", lang, name=name)
            
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(
                        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                        json={
                            "chat_id": user["telegram_id"],
                            "text": message,
                            "parse_mode": "HTML"
                        },
                        timeout=10
                    )
                
                # Update last_reengagement_at
                db.client.table("users").update({
                    "last_reengagement_at": now.isoformat()
                }).eq("id", user["id"]).execute()
                
                sent_count += 1
            except Exception as e:
                print(f"Failed to send to {user['telegram_id']}: {e}")
        
        results["tasks"]["reengagement_sent"] = sent_count
        
        # 2. Wishlist reminders (items added 3+ days ago, not reminded yet)
        wishlist_cutoff = now - timedelta(days=3)
        wishlist_items = db.client.table("wishlist").select(
            "id,user_id,product_name,users(telegram_id,language_code)"
        ).eq("reminded", False).lt(
            "created_at", wishlist_cutoff.isoformat()
        ).limit(50).execute()
        
        wishlist_sent = 0
        for item in (wishlist_items.data or []):
            user_data = item.get("users", {})
            if not user_data:
                continue
            
            lang = user_data.get("language_code", "en")
            message = get_text(
                "wishlist_reminder", lang, 
                product=item.get("product_name", "")
            )
            
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(
                        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                        json={
                            "chat_id": user_data["telegram_id"],
                            "text": message,
                            "parse_mode": "HTML"
                        },
                        timeout=10
                    )
                
                # Mark as reminded
                db.client.table("wishlist").update({
                    "reminded": True
                }).eq("id", item["id"]).execute()
                
                wishlist_sent += 1
            except Exception as e:
                print(f"Failed wishlist reminder: {e}")
        
        results["tasks"]["wishlist_reminders_sent"] = wishlist_sent
        
        # 3. Expiring subscription notifications (3 days before expiry)
        expiry_window_start = now + timedelta(days=2)
        expiry_window_end = now + timedelta(days=4)
        
        expiring_orders = db.client.table("orders").select(
            "id,user_id,product_id,expires_at,products(name),users(telegram_id,language_code)"
        ).eq("status", "completed").gte(
            "expires_at", expiry_window_start.isoformat()
        ).lte("expires_at", expiry_window_end.isoformat()).limit(50).execute()
        
        expiry_sent = 0
        for order in (expiring_orders.data or []):
            user_data = order.get("users", {})
            product_data = order.get("products", {})
            if not user_data or not product_data:
                continue
            
            lang = user_data.get("language_code", "en")
            days_left = 3
            message = get_text(
                "subscription_expiring", lang,
                product=product_data.get("name", ""),
                days=days_left
            )
            
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(
                        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                        json={
                            "chat_id": user_data["telegram_id"],
                            "text": message,
                            "parse_mode": "HTML"
                        },
                        timeout=10
                    )
                expiry_sent += 1
            except Exception as e:
                print(f"Failed expiry notification: {e}")
        
        results["tasks"]["expiry_notifications_sent"] = expiry_sent
        results["success"] = True
        
    except Exception as e:
        results["success"] = False
        results["error"] = str(e)
    
    return JSONResponse(results)

