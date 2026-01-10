"""
Daily Cleanup Cron Job
Schedule: 0 3 * * * (3:00 AM UTC daily)

Tasks:
1. Clear expired cart reservations (older than 24h)
2. Clear old chat history (older than 30 days)
3. Clean up expired promo codes
4. Release stuck stock reservations
"""
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import os

# Verify cron secret to prevent unauthorized access
CRON_SECRET = os.environ.get("CRON_SECRET", "")

# ASGI app (only export app to Vercel, avoid 'handler' symbol)
app = FastAPI()


@app.get("/api/cron/daily_cleanup")
async def daily_cleanup_entrypoint(request: Request):
    """
    Vercel Cron entrypoint for daily cleanup tasks.
    """
    auth_header = request.headers.get("Authorization", "")
    if CRON_SECRET and auth_header != f"Bearer {CRON_SECRET}":
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    from core.services.database import get_database
    
    db = get_database()
    now = datetime.now(timezone.utc)
    results = {
        "timestamp": now.isoformat(),
        "tasks": {}
    }
    
    try:
        # 1. Release stuck stock reservations (older than 30 min)
        cutoff_reservations = now - timedelta(minutes=30)
        stuck_reservations = await db.client.table("stock_items").update({
            "status": "available",
            "reserved_at": None
        }).eq("status", "reserved").lt(
            "reserved_at", cutoff_reservations.isoformat()
        ).execute()
        results["tasks"]["released_reservations"] = len(stuck_reservations.data or [])
        
        # 2. Clear old chat history (older than 30 days)
        cutoff_chat = now - timedelta(days=30)
        old_chats = await db.client.table("chat_history").delete().lt(
            "timestamp", cutoff_chat.isoformat()
        ).execute()
        results["tasks"]["deleted_old_chats"] = len(old_chats.data or [])
        
        # 3. Deactivate expired promo codes
        expired_promos = await db.client.table("promo_codes").update({
            "is_active": False
        }).eq("is_active", True).lt(
            "expires_at", now.isoformat()
        ).execute()
        results["tasks"]["expired_promos"] = len(expired_promos.data or [])
        
        # 4. Clean wishlist items older than 90 days that have been reminded
        cutoff_wishlist = now - timedelta(days=90)
        old_wishlist = await db.client.table("wishlist").delete().eq(
            "reminded", True
        ).lt("created_at", cutoff_wishlist.isoformat()).execute()
        results["tasks"]["cleaned_wishlist"] = len(old_wishlist.data or [])
        
        results["success"] = True
        
    except Exception as e:
        results["success"] = False
        results["error"] = str(e)
    
    return JSONResponse(results)
