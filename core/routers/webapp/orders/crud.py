"""
Order CRUD Endpoints

Order history, status, and payment method endpoints.
All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, Query

from core.services.database import get_database
from core.auth import verify_telegram_auth
from ..models import (
    OrderHistoryResponse, 
    OrderStatusResponse, 
    PaymentMethodsResponse, 
    PaymentMethod,
)

logger = logging.getLogger(__name__)

crud_router = APIRouter()


@crud_router.get("/orders/{order_id}/status")
async def get_webapp_order_status(order_id: str, user=Depends(verify_telegram_auth)) -> OrderStatusResponse:
    """Get order status with delivery progress."""
    db = get_database()
    
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    result = await db.client.table("orders").select(
        "*, order_items(*)"
    ).eq("id", order_id).single().execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Order not found")
    
    order = result.data
    
    if order["user_id"] != db_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Calculate delivery progress
    items_data = order.get("order_items", [])
    total_quantity = sum(item.get("quantity", 0) for item in items_data)
    delivered_quantity = sum(item.get("delivered_quantity", 0) for item in items_data)
    
    progress = 0
    if total_quantity > 0:
        progress = int((delivered_quantity / total_quantity) * 100)
    
    # Calculate estimated delivery
    estimated_delivery_at = None
    if order["status"] in ("paid", "processing", "partially_delivered"):
        max_hours = 0
        for item in items_data:
            hours = item.get("fulfillment_time_hours") or 24
            max_hours = max(max_hours, hours)
        
        paid_at = order.get("paid_at") or order.get("created_at")
        if paid_at:
            try:
                paid_dt = datetime.fromisoformat(paid_at.replace("Z", "+00:00"))
                est_dt = paid_dt + timedelta(hours=max_hours)
                estimated_delivery_at = est_dt.isoformat()
            except Exception:
                pass
    
    return OrderStatusResponse(
        order_id=order_id,
        status=order["status"],
        progress=progress,
        delivered_quantity=delivered_quantity,
        total_quantity=total_quantity,
        estimated_delivery_at=estimated_delivery_at,
        payment_url=order.get("payment_url")
    )


@crud_router.post("/orders/{order_id}/verify-payment")
async def verify_order_payment(order_id: str, user=Depends(verify_telegram_auth)):
    """
    Manually verify payment status via payment gateway.
    Useful for checking payment on popup/window close.
    """
    from core.routers.deps import get_payment_service
    
    db = get_database()
    
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    result = await db.client.table("orders").select("*").eq(
        "id", order_id
    ).single().execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Order not found")
    
    order = result.data
    
    if order["user_id"] != db_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Already processed
    if order["status"] in ("paid", "delivered", "completed"):
        return {"status": order["status"], "verified": True}
    
    # Check payment gateway status
    payment_id = order.get("payment_id")
    payment_gateway = order.get("payment_gateway")
    
    if not payment_id:
        return {"status": order["status"], "verified": False, "message": "No payment_id"}
    
    if payment_gateway == "crystalpay":
        payment_service = get_payment_service()
        try:
            invoice_info = await payment_service.get_invoice_info(payment_id)
            if invoice_info:
                gateway_status = invoice_info.get("state", "")
                
                if gateway_status == "payed":
                    # Payment confirmed by gateway - process it
                    from core.orders.status_service import OrderStatusService
                    status_service = OrderStatusService(db)
                    final_status = await status_service.mark_payment_confirmed(
                        order_id=order_id,
                        payment_id=payment_id,
                        check_stock=True
                    )
                    
                    # Queue delivery
                    try:
                        from core.queue import publish_to_worker, WorkerEndpoints
                        await publish_to_worker(
                            endpoint=WorkerEndpoints.DELIVER_GOODS,
                            body={"order_id": order_id},
                            retries=2,
                            deduplication_id=f"deliver-{order_id}"
                        )
                    except Exception as e:
                        logger.warning(f"Failed to queue delivery for {order_id}: {e}")
                    
                    return {"status": final_status, "verified": True}
                elif gateway_status == "processing":
                    return {"status": "processing", "verified": False, "message": "Payment is being processed"}
                elif gateway_status in ("notpayed", "failed"):
                    return {"status": order["status"], "verified": False, "message": "Payment not received"}
        except Exception as e:
            logger.warning(f"Failed to verify payment for order {order_id}: {e}")
            return {"status": order["status"], "verified": False, "message": "Verification failed"}
    
    return {"status": order["status"], "verified": False, "message": "Unknown gateway"}


@crud_router.get("/orders")
async def get_webapp_orders(
    user=Depends(verify_telegram_auth),
    status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
) -> List[OrderHistoryResponse]:
    """Get user's order history with filtering."""
    logger.info(f"[DEBUG] get_webapp_orders ENTRY: telegram_id={user.id}, status={status}, limit={limit}, offset={offset}")
    
    from core.db import get_redis
    from core.services.currency import get_currency_service
    
    db = get_database()
    redis = get_redis()
    currency_service = get_currency_service(redis)
    
    db_user = await db.get_user_by_telegram_id(user.id)
    logger.info(f"[DEBUG] after get_user_by_telegram_id: telegram_id={user.id}, db_user_id={db_user.id if db_user else None}, db_user_exists={db_user is not None}")
    
    if not db_user:
        logger.error(f"[DEBUG] User not found: telegram_id={user.id}")
        raise HTTPException(status_code=404, detail="User not found")
    
    # Build query
    query = db.client.table("orders").select("*, order_items(*, product:products(*))").eq("user_id", db_user.id)
    
    if status:
        query = query.eq("status", status)
    
    query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
    
    logger.info(f"[DEBUG] before query.execute: user_id={db_user.id}, status_filter={status}")
    
    try:
        result = await query.execute()
        logger.info(f"[DEBUG] after query.execute: result_count={len(result.data) if result.data else 0}, has_data={result.data is not None}")
    except Exception as e:
        logger.error(f"[DEBUG] query.execute exception: {type(e).__name__}: {e}", exc_info=True)
        logger.error(f"Failed to fetch orders for user {db_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch orders")
    
    if not result.data:
        logger.info(f"[DEBUG] No orders found: user_id={db_user.id}, telegram_id={user.id}")
        logger.info(f"No orders found for user {db_user.id} (telegram_id={user.id})")
        return []
    
    # Get user's preferred currency
    user_lang = getattr(db_user, 'interface_language', None) or (db_user.language_code if db_user and db_user.language_code else user.language_code)
    preferred_currency = getattr(db_user, 'preferred_currency', None)
    user_currency = currency_service.get_user_currency(user_lang, preferred_currency)
    
    logger.info(f"[DEBUG] starting order processing: total_orders={len(result.data)}, user_id={db_user.id}")
    logger.info(f"Processing {len(result.data)} orders for user {db_user.id}")
    
    orders = []
    processed_count = 0
    error_count = 0
    for row in result.data:
        try:
            items_data = row.get("order_items", [])
            logger.info(f"[DEBUG] processing order: order_id={row.get('id')}, has_items={bool(items_data)}, items_count={len(items_data) if items_data else 0}")
            
            if not items_data:
                logger.warning(f"Order {row.get('id')} has no order_items")
                continue
            
            # Get first product for main display
            first_item = items_data[0] if items_data else None
            product_data = first_item.get("product") if first_item else None
            
            # Get first item's image for display
            main_image_url = None
            if product_data:
                main_image_url = product_data.get("image_url")
            
            # Calculate progress
            total_quantity = sum(item.get("quantity", 0) for item in items_data)
            delivered_quantity = sum(item.get("delivered_quantity", 0) for item in items_data)
            progress = 0
            if total_quantity > 0:
                progress = int((delivered_quantity / total_quantity) * 100)
            
            # Build items list
            items = []
            for item in items_data:
                prod = item.get("product")
                items.append({
                    "product_id": item.get("product_id"),
                    "product_name": prod.get("name") if prod else "Unknown",
                    "quantity": item.get("quantity", 1),
                    "instant_quantity": item.get("instant_quantity", 0),
                    "prepaid_quantity": item.get("prepaid_quantity", 0),
                    "delivered_quantity": item.get("delivered_quantity", 0),
                    "amount": float(item.get("amount", 0)),
                    "image_url": prod.get("image_url") if prod else None,
                })
            
            # Convert amount to user's currency
            usd_amount = float(row.get("amount", 0))
            logger.info(f"[DEBUG] before currency conversion: order_id={row.get('id')}, usd_amount={usd_amount}, user_currency={user_currency}")
            
            display_amount = await currency_service.convert_price(usd_amount, user_currency)
            formatted_amount = currency_service.format_price(display_amount, user_currency)
            
            orders.append(OrderHistoryResponse(
                order_id=row["id"],
                status=row["status"],
                amount=usd_amount,
                display_amount=formatted_amount,
                display_currency=user_currency,
                created_at=row.get("created_at"),
                product_name=product_data.get("name") if product_data else "Multiple items",
                quantity=total_quantity,
                delivered_quantity=delivered_quantity,
                progress=progress,
                payment_method=row.get("payment_method"),
                payment_url=row.get("payment_url"),
                items=items,
                image_url=main_image_url,
            ))
            processed_count += 1
        except Exception as e:
            error_count += 1
            logger.error(f"[DEBUG] order processing exception: order_id={row.get('id')}, error={type(e).__name__}: {e}", exc_info=True)
            logger.error(f"Failed to process order {row.get('id')}: {e}", exc_info=True)
            # Continue processing other orders instead of failing entirely
            continue
    
    logger.info(f"[DEBUG] returning orders: total_orders={len(result.data)}, processed={processed_count}, errors={error_count}, returning={len(orders)}")
    logger.info(f"Returning {len(orders)} orders for user {db_user.id}")
    return orders


@crud_router.get("/payments/methods")
async def get_payment_methods(
    user=Depends(verify_telegram_auth),
    amount: Optional[float] = Query(None, description="Order amount in user's currency for availability check"),
    currency: Optional[str] = Query(None, description="Currency code (RUB, USD, etc)")
) -> PaymentMethodsResponse:
    """
    Get available payment methods for user based on their region and balance.
    Returns methods sorted by preference for the user's locale.
    """
    from core.db import get_redis
    from core.services.currency import get_currency_service
    
    db = get_database()
    redis = get_redis()
    currency_service = get_currency_service(redis)
    
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Determine user's currency
    user_lang = getattr(db_user, 'interface_language', None) or (db_user.language_code if db_user and db_user.language_code else user.language_code)
    preferred_currency = getattr(db_user, 'preferred_currency', None)
    user_currency = currency or currency_service.get_user_currency(user_lang, preferred_currency)
    
    # Get user balance
    user_balance = float(db_user.balance or 0)
    balance_currency = getattr(db_user, 'balance_currency', 'USD') or 'USD'
    
    methods = []
    
    # 1. Balance payment (always available if > 0)
    if user_balance > 0:
        balance_display = currency_service.format_price(user_balance, balance_currency)
        
        # Check if balance is sufficient for the order
        balance_sufficient = True
        if amount:
            # Convert amount to balance currency
            if user_currency == balance_currency:
                amount_in_balance_currency = amount
            else:
                # First convert user's currency amount to USD, then to balance currency
                try:
                    user_rate = await currency_service.get_exchange_rate(user_currency)
                    balance_rate = await currency_service.get_exchange_rate(balance_currency)
                    usd_amount = amount / user_rate if user_rate > 0 else amount
                    amount_in_balance_currency = usd_amount * balance_rate
                except Exception:
                    amount_in_balance_currency = amount
            
            balance_sufficient = user_balance >= amount_in_balance_currency
        
        methods.append(PaymentMethod(
            id="balance",
            name="Баланс аккаунта",
            description=f"Доступно: {balance_display}",
            icon="wallet",
            available=balance_sufficient,
            min_amount=None,
            max_amount=user_balance,
            fee_percent=0,
            processing_time="Мгновенно",
            currency=balance_currency
        ))
    
    # 2. CrystalPay card payment
    methods.append(PaymentMethod(
        id="card",
        name="Банковская карта",
        description="Visa, MasterCard, МИР",
        icon="credit-card",
        available=True,
        min_amount=10 if user_currency == "RUB" else 0.5,
        max_amount=100000 if user_currency == "RUB" else 5000,
        fee_percent=0,
        processing_time="1-5 минут",
        currency=user_currency
    ))
    
    # 3. SBP (for Russian users)
    if user_currency == "RUB" or user_lang in ("ru", "ru-RU"):
        methods.append(PaymentMethod(
            id="sbp",
            name="СБП",
            description="Система быстрых платежей",
            icon="zap",
            available=True,
            min_amount=10,
            max_amount=600000,
            fee_percent=0,
            processing_time="Мгновенно",
            currency="RUB"
        ))
    
    # 4. Crypto
    methods.append(PaymentMethod(
        id="crypto",
        name="Криптовалюта",
        description="BTC, ETH, USDT, TON",
        icon="bitcoin",
        available=True,
        min_amount=1 if user_currency == "USD" else 100,
        max_amount=None,
        fee_percent=0,
        processing_time="10-30 минут",
        currency="USD"
    ))
    
    # Calculate default recommendation
    recommended = "card"
    if user_balance > 0 and amount and user_balance >= amount:
        recommended = "balance"
    elif user_currency == "RUB":
        recommended = "sbp"
    
    return PaymentMethodsResponse(
        methods=methods,
        default_currency=user_currency,
        recommended_method=recommended
    )
