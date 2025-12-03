"""
Cron job endpoints for scheduled tasks.

Called by Vercel Cron with CRON_SECRET authentication.
"""
import os
from datetime import datetime, timedelta

from fastapi import APIRouter, Header, HTTPException

from src.services.database import get_database
from core.routers.deps import get_notification_service

router = APIRouter(prefix="/api/cron", tags=["cron"])


def _verify_cron_secret(authorization: str) -> None:
    """Verify cron job authentication."""
    cron_secret = os.environ.get("CRON_SECRET", "")
    if authorization != f"Bearer {cron_secret}":
        raise HTTPException(status_code=401, detail="Invalid cron secret")


@router.get("/review-requests")
async def cron_review_requests(authorization: str = Header(None)):
    """
    Send review requests for orders completed 1 hour ago.
    Called by Vercel Cron every 15 minutes.
    """
    _verify_cron_secret(authorization)
    
    db = get_database()
    
    # Get orders completed ~1 hour ago (between 45-75 minutes)
    now = datetime.utcnow()
    start_time = now - timedelta(minutes=75)
    end_time = now - timedelta(minutes=45)
    
    orders = db.client.table("orders").select("id").eq(
        "status", "completed"
    ).gte("delivered_at", start_time.isoformat()).lte(
        "delivered_at", end_time.isoformat()
    ).execute()
    
    notification_service = get_notification_service()
    
    sent_count = 0
    for order in orders.data:
        # Check if review already exists
        existing = db.client.table("reviews").select("id").eq("order_id", order["id"]).execute()
        if not existing.data:
            await notification_service.send_review_request(order["id"])
            sent_count += 1
    
    return {"sent": sent_count}


@router.get("/expiration-reminders")
async def cron_expiration_reminders(authorization: str = Header(None)):
    """
    Send reminders for subscriptions expiring in 3 days.
    Called by Vercel Cron daily.
    """
    _verify_cron_secret(authorization)
    
    db = get_database()
    
    # Get orders expiring in 3 days
    orders = await db.get_expiring_orders(days_before=3)
    
    notification_service = get_notification_service()
    
    sent_count = 0
    for order in orders:
        # Get user and product info
        user_result = db.client.table("users").select(
            "telegram_id,language_code"
        ).eq("id", order.user_id).execute()
        
        product = await db.get_product_by_id(order.product_id)
        
        if user_result.data and product:
            user = user_result.data[0]
            days_left = (order.expires_at - datetime.utcnow()).days if order.expires_at else 0
            
            await notification_service.send_expiration_reminder(
                telegram_id=user["telegram_id"],
                product_name=product.name,
                days_left=days_left,
                language=user.get("language_code", "en")
            )
            sent_count += 1
    
    return {"sent": sent_count}


@router.get("/wishlist-reminders")
async def cron_wishlist_reminders(authorization: str = Header(None)):
    """
    Send reminders for items in wishlist for 3+ days.
    Called by Vercel Cron daily.
    """
    _verify_cron_secret(authorization)
    
    db = get_database()
    
    # Get wishlist items older than 3 days that haven't been reminded
    cutoff = datetime.utcnow() - timedelta(days=3)
    
    items = db.client.table("wishlist").select(
        "id,user_id,product_id,products(name,stock_count:stock_items(count))"
    ).eq("reminded", False).lt("created_at", cutoff.isoformat()).execute()
    
    notification_service = get_notification_service()
    
    sent_count = 0
    for item in items.data:
        # Get user
        user_result = db.client.table("users").select(
            "telegram_id,language_code,do_not_disturb"
        ).eq("id", item["user_id"]).execute()
        
        if not user_result.data:
            continue
        
        user = user_result.data[0]
        if user.get("do_not_disturb"):
            continue
        
        product_name = item.get("products", {}).get("name", "Product")
        
        from src.i18n import get_text
        message = get_text(
            "wishlist_reminder",
            user.get("language_code", "en"),
            product=product_name
        )
        
        bot = notification_service._get_bot()
        if bot:
            try:
                await bot.send_message(chat_id=user["telegram_id"], text=message)
                
                # Mark as reminded
                db.client.table("wishlist").update({
                    "reminded": True
                }).eq("id", item["id"]).execute()
                
                sent_count += 1
            except Exception as e:
                print(f"Failed to send wishlist reminder: {e}")
    
    return {"sent": sent_count}


@router.get("/re-engagement")
async def cron_re_engagement(authorization: str = Header(None)):
    """
    Send re-engagement messages to inactive users (7+ days).
    Called by Vercel Cron daily.
    """
    _verify_cron_secret(authorization)
    
    db = get_database()
    
    # Get users inactive for 7+ days
    cutoff = datetime.utcnow() - timedelta(days=7)
    
    users = db.client.table("users").select(
        "telegram_id,language_code"
    ).eq("is_banned", False).eq("do_not_disturb", False).lt(
        "last_activity_at", cutoff.isoformat()
    ).limit(50).execute()
    
    notification_service = get_notification_service()
    bot = notification_service._get_bot()
    
    if not bot:
        return {"sent": 0}
    
    sent_count = 0
    for user in users.data:
        lang = user.get("language_code", "en")
        
        # Personalized re-engagement message
        message = {
            "ru": "👋 Давно не виделись! У нас появились новые предложения. Может, поможем найти что-то интересное?",
            "en": "👋 Long time no see! We have new offers. Can we help you find something interesting?",
        }.get(lang, "👋 Long time no see! We have new offers. Can we help you find something interesting?")
        
        try:
            await bot.send_message(chat_id=user["telegram_id"], text=message)
            sent_count += 1
        except Exception:
            pass  # User may have blocked the bot
    
    return {"sent": sent_count}


@router.get("/daily-tasks")
async def cron_daily_tasks(authorization: str = Header(None)):
    """
    Combined daily cron job for Hobby plan (max 2 crons, once per day).
    Runs ALL scheduled tasks:
    - Review requests (orders completed yesterday)
    - Expiration reminders (subscriptions expiring in 3 days)
    - Wishlist reminders (items saved 3+ days ago)
    - Re-engagement (users inactive 7+ days)
    """
    _verify_cron_secret(authorization)
    
    results = {
        "review_requests": 0,
        "expiration_reminders": 0,
        "wishlist_reminders": 0,
        "re_engagement": 0,
        "rag_indexed": 0
    }
    
    notification_service = get_notification_service()
    db = get_database()
    bot = notification_service._get_bot()
    
    # -1. Index products for RAG (semantic search)
    try:
        from core.rag import get_product_search
        search = get_product_search()
        if search.is_available:
            indexed = await search.index_all_products()
            results["rag_indexed"] = indexed
    except Exception as e:
        print(f"RAG indexing error: {e}")
    
    if not bot:
        return {"error": "Bot not configured", "results": results}
    
    # 0. Review requests (orders completed yesterday)
    try:
        yesterday_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
        yesterday_end = yesterday_start + timedelta(days=1)
        
        orders = db.client.table("orders").select("id").eq(
            "status", "completed"
        ).gte("delivered_at", yesterday_start.isoformat()).lt(
            "delivered_at", yesterday_end.isoformat()
        ).is_("review_requested_at", "null").execute()
        
        for order in orders.data:
            existing_review = db.client.table("reviews").select("id").eq("order_id", order["id"]).execute()
            if not existing_review.data:
                await notification_service.send_review_request(order["id"])
                db.client.table("orders").update(
                    {"review_requested_at": datetime.utcnow().isoformat()}
                ).eq("id", order["id"]).execute()
                results["review_requests"] += 1
    except Exception as e:
        print(f"Review requests error: {e}")
    
    # 1. Expiration reminders (subscriptions expiring in 3 days)
    try:
        orders = await db.get_expiring_orders(days_before=3)
        for order in orders:
            user_result = db.client.table("users").select(
                "telegram_id,language_code"
            ).eq("id", order.user_id).execute()
            product = await db.get_product_by_id(order.product_id)
            
            if user_result.data and product:
                user = user_result.data[0]
                days_left = (order.expires_at - datetime.utcnow()).days if order.expires_at else 0
                await notification_service.send_expiration_reminder(
                    telegram_id=user["telegram_id"],
                    product_name=product.name,
                    days_left=days_left,
                    language=user.get("language_code", "en")
                )
                results["expiration_reminders"] += 1
    except Exception as e:
        print(f"Expiration reminders error: {e}")
    
    # 2. Wishlist reminders (items saved 3+ days ago)
    try:
        from src.i18n import get_text
        cutoff = datetime.utcnow() - timedelta(days=3)
        items = db.client.table("wishlist").select(
            "id,user_id,products(name)"
        ).eq("reminded", False).lt("created_at", cutoff.isoformat()).limit(20).execute()
        
        for item in items.data:
            user_result = db.client.table("users").select(
                "telegram_id,language_code,do_not_disturb"
            ).eq("id", item["user_id"]).execute()
            
            if user_result.data and not user_result.data[0].get("do_not_disturb"):
                user = user_result.data[0]
                try:
                    msg = get_text("wishlist_reminder", user.get("language_code", "en"), 
                                  product=item.get("products", {}).get("name", "Product"))
                    await bot.send_message(chat_id=user["telegram_id"], text=msg)
                    db.client.table("wishlist").update({"reminded": True}).eq("id", item["id"]).execute()
                    results["wishlist_reminders"] += 1
                except Exception:
                    pass
    except Exception as e:
        print(f"Wishlist reminders error: {e}")
    
    # 3. Re-engagement (users inactive 7+ days)
    try:
        cutoff = datetime.utcnow() - timedelta(days=7)
        users = db.client.table("users").select(
            "telegram_id,language_code"
        ).eq("is_banned", False).eq("do_not_disturb", False).lt(
            "last_activity_at", cutoff.isoformat()
        ).limit(30).execute()
        
        for user in users.data:
            lang = user.get("language_code", "en")
            msg = {
                "ru": "👋 Давно не виделись! У нас появились новые предложения.",
                "en": "👋 Long time no see! We have new offers."
            }.get(lang, "👋 Long time no see! We have new offers.")
            try:
                await bot.send_message(chat_id=user["telegram_id"], text=msg)
                results["re_engagement"] += 1
            except Exception:
                pass
    except Exception as e:
        print(f"Re-engagement error: {e}")
    
    return results

