"""
Profile Tools for Shop Agent.

User profile, referral info, balance history.
All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""
from langchain_core.tools import tool

from core.logging import get_logger
from .base import get_db, get_user_context

logger = get_logger(__name__)


@tool
async def get_user_profile() -> dict:
    """
    Get user's full profile information.
    Loads thresholds from referral_settings, converts balance to user currency.
    Uses user_id and currency from context.
        
    Returns:
        Complete profile with balance, career level, stats
    """
    try:
        from core.db import get_redis
        from core.services.currency import get_currency_service
        
        ctx = get_user_context()
        db = get_db()
        
        settings_result = await db.client.table("referral_settings").select("*").limit(1).execute()
        
        if settings_result.data:
            s = settings_result.data[0]
            threshold_l2 = float(s.get("level2_threshold_usd", 250) or 250)
            threshold_l3 = float(s.get("level3_threshold_usd", 1000) or 1000)
        else:
            threshold_l2, threshold_l3 = 250, 1000
        
        result = await db.client.table("users").select("*").eq("id", ctx.user_id).single().execute()
        
        if not result.data:
            return {"success": False, "error": "User not found"}
        
        user = result.data
        balance = float(user.get("balance", 0) or 0)
        turnover = float(user.get("turnover_usd", 0) or 0)
        total_saved = float(user.get("total_saved", 0) or 0)
        referral_earnings = float(user.get("total_referral_earnings", 0) or 0)
        
        # Check VIP status - VIP always gets ARCHITECT level
        is_partner = user.get("is_partner", False)
        partner_override = user.get("partner_level_override")
        
        if is_partner and partner_override is not None:
            # VIP with level override - always ARCHITECT
            career_level = "ARCHITECT"
            next_level = None
            turnover_to_next = 0
        else:
            line1_unlocked = user.get("level1_unlocked_at") is not None or user.get("referral_program_unlocked", False)
            line2_unlocked = turnover >= threshold_l2 or user.get("level2_unlocked_at") is not None
            line3_unlocked = turnover >= threshold_l3 or user.get("level3_unlocked_at") is not None
            
            if line3_unlocked:
                career_level = "ARCHITECT"
                next_level = None
                turnover_to_next = 0
            elif line2_unlocked:
                career_level = "OPERATOR"
                next_level = "ARCHITECT"
                turnover_to_next = max(0, threshold_l3 - turnover)
            elif line1_unlocked:
                career_level = "PROXY"
                next_level = "OPERATOR"
                turnover_to_next = max(0, threshold_l2 - turnover)
            else:
                career_level = "LOCKED"
                next_level = "PROXY (make first purchase)"
                turnover_to_next = 0
        
        orders_result = await db.client.table("orders").select(
            "id", count="exact"
        ).eq("user_id", ctx.user_id).execute()
        orders_count = orders_result.count or 0
        
        redis = get_redis()
        currency_service = get_currency_service(redis)
        target_currency = ctx.currency
        
        if target_currency != "USD" and balance > 0:
            try:
                balance_converted = await currency_service.convert_price(balance, target_currency)
            except Exception:
                balance_converted = balance
        else:
            balance_converted = balance
        
        if target_currency != "USD":
            try:
                total_saved_converted = await currency_service.convert_price(total_saved, target_currency)
                referral_earnings_converted = await currency_service.convert_price(referral_earnings, target_currency)
            except Exception:
                total_saved_converted = total_saved
                referral_earnings_converted = referral_earnings
        else:
            total_saved_converted = total_saved
            referral_earnings_converted = referral_earnings
        
        return {
            "success": True,
            "balance": balance_converted,
            "balance_usd": balance,
            "currency": target_currency,
            "balance_formatted": currency_service.format_price(balance_converted, target_currency),
            "career_level": career_level,
            "turnover_usd": turnover,
            "next_level": next_level,
            "turnover_to_next_usd": turnover_to_next,
            "total_saved": total_saved,
            "total_saved_formatted": currency_service.format_price(total_saved_converted, target_currency),
            "referral_earnings": referral_earnings,
            "referral_earnings_formatted": currency_service.format_price(referral_earnings_converted, target_currency),
            "orders_count": orders_count,
            "partner_mode": user.get("partner_mode", "commission"),
        }
    except Exception as e:
        logger.error(f"get_user_profile error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@tool
async def get_referral_info() -> dict:
    """
    Get user's referral program info.
    Loads settings from database (referral_settings table).
    Uses user_id and telegram_id from context.
        
    Returns:
        Complete referral info with link, earnings, network stats
    """
    try:
        ctx = get_user_context()
        db = get_db()
        
        settings_result = await db.client.table("referral_settings").select("*").limit(1).execute()
        
        if settings_result.data:
            s = settings_result.data[0]
            threshold_l2 = float(s.get("level2_threshold_usd", 250) or 250)
            threshold_l3 = float(s.get("level3_threshold_usd", 1000) or 1000)
            commission_l1 = float(s.get("level1_commission_percent", 10) or 10)
            commission_l2 = float(s.get("level2_commission_percent", 7) or 7)
            commission_l3 = float(s.get("level3_commission_percent", 3) or 3)
        else:
            threshold_l2, threshold_l3 = 250, 1000
            commission_l1, commission_l2, commission_l3 = 10, 7, 3
        
        result = await db.client.table("users").select(
            "balance, turnover_usd, total_referral_earnings, partner_mode, partner_discount_percent, "
            "level1_unlocked_at, level2_unlocked_at, level3_unlocked_at, referral_program_unlocked"
        ).eq("id", ctx.user_id).single().execute()
        
        if not result.data:
            return {"success": False, "error": "User not found"}
        
        user = result.data
        turnover = float(user.get("turnover_usd", 0) or 0)
        earnings = float(user.get("total_referral_earnings", 0) or 0)
        
        line1_unlocked = user.get("level1_unlocked_at") is not None or user.get("referral_program_unlocked", False)
        line2_unlocked = turnover >= threshold_l2 or user.get("level2_unlocked_at") is not None
        line3_unlocked = turnover >= threshold_l3 or user.get("level3_unlocked_at") is not None
        
        if line3_unlocked:
            career_level = "ARCHITECT"
            next_level = None
            turnover_to_next = 0
        elif line2_unlocked:
            career_level = "OPERATOR"
            next_level = "ARCHITECT"
            turnover_to_next = max(0, threshold_l3 - turnover)
        elif line1_unlocked:
            career_level = "PROXY"
            next_level = "OPERATOR"
            turnover_to_next = max(0, threshold_l2 - turnover)
        else:
            career_level = "LOCKED"
            next_level = "PROXY"
            turnover_to_next = 0
        
        network = {"line1": 0, "line2": 0, "line3": 0}
        
        l1 = await db.client.table("users").select("id", count="exact").eq(
            "referrer_id", ctx.user_id
        ).execute()
        network["line1"] = l1.count or 0
        
        l1_ids = [u["id"] for u in (l1.data or [])]
        if l1_ids and line2_unlocked:
            l2 = await db.client.table("users").select("id", count="exact").in_(
                "referrer_id", l1_ids
            ).execute()
            network["line2"] = l2.count or 0
            
            l2_ids = [u["id"] for u in (l2.data or [])]
            if l2_ids and line3_unlocked:
                l3 = await db.client.table("users").select("id", count="exact").in_(
                    "referrer_id", l2_ids
                ).execute()
                network["line3"] = l3.count or 0
        
        active_commissions = {}
        if line1_unlocked:
            active_commissions["line1"] = commission_l1
        if line2_unlocked:
            active_commissions["line2"] = commission_l2
        if line3_unlocked:
            active_commissions["line3"] = commission_l3
        
        partner_mode = user.get("partner_mode", "commission")
        
        return {
            "success": True,
            "referral_link": f"https://t.me/pvndora_ai_bot?start=ref_{ctx.telegram_id}",
            "career_level": career_level,
            "line1_unlocked": line1_unlocked,
            "line2_unlocked": line2_unlocked,
            "line3_unlocked": line3_unlocked,
            "turnover_usd": turnover,
            "next_level": next_level,
            "turnover_to_next_usd": turnover_to_next,
            "thresholds": {"level2": threshold_l2, "level3": threshold_l3},
            "total_earnings": earnings,
            "network": network,
            "total_referrals": sum(network.values()),
            "active_commissions": active_commissions,
            "all_commissions": {"line1": commission_l1, "line2": commission_l2, "line3": commission_l3},
            "partner_mode": partner_mode,
            "discount_percent": user.get("partner_discount_percent", 0) if partner_mode == "discount" else 0,
            "balance": float(user.get("balance", 0) or 0),
        }
    except Exception as e:
        logger.error(f"get_referral_info error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@tool
async def get_balance_history(limit: int = 10) -> dict:
    """
    Get user's balance transaction history.
    Shows deposits, purchases, referral earnings, cashback, etc.
    Uses user_id from context.
    
    Args:
        limit: Max transactions to return
        
    Returns:
        List of balance transactions
    """
    try:
        from core.db import get_redis
        from core.services.currency import get_currency_service
        
        ctx = get_user_context()
        db = get_db()
        
        result = await db.client.table("balance_transactions").select("*").eq(
            "user_id", ctx.user_id
        ).order("created_at", desc=True).limit(limit).execute()
        
        if not result.data:
            return {
                "success": True,
                "count": 0,
                "transactions": [],
                "message": "Нет транзакций"
            }
        
        redis = get_redis()
        currency_service = get_currency_service(redis)
        
        transactions = []
        for tx in result.data:
            amount_usd = float(tx.get("amount", 0))
            
            if ctx.currency != "USD":
                try:
                    amount_display = await currency_service.convert_price(abs(amount_usd), ctx.currency)
                except Exception:
                    amount_display = abs(amount_usd)
            else:
                amount_display = abs(amount_usd)
            
            sign = "+" if amount_usd > 0 else "-"
            
            type_labels = {
                "referral_bonus": "Реферальный бонус",
                "purchase": "Покупка",
                "deposit": "Пополнение",
                "cashback": "Кэшбэк за отзыв",
                "refund": "Возврат",
                "withdrawal": "Вывод средств"
            }
            
            transactions.append({
                "type": tx.get("type"),
                "type_label": type_labels.get(tx.get("type"), tx.get("type")),
                "amount": amount_display,
                "amount_formatted": f"{sign}{currency_service.format_price(amount_display, ctx.currency)}",
                "description": tx.get("description", ""),
                "created_at": tx.get("created_at"),
            })
        
        return {
            "success": True,
            "count": len(transactions),
            "transactions": transactions
        }
    except Exception as e:
        logger.error(f"get_balance_history error: {e}")
        return {"success": False, "error": str(e)}
