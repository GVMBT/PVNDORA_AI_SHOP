"""Admin Orders & FAQ Router.

Order and FAQ management endpoints.
All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.auth import verify_admin
from core.logging import get_logger
from core.routers.deps import get_payment_service
from core.services.database import get_database

from .models import CreateFAQRequest

logger = get_logger(__name__)
router = APIRouter(tags=["admin-orders"])


# ==================== ORDERS ====================


# Helper: Format order for admin panel (reduces cognitive complexity)
def _format_order_for_admin(order: dict) -> dict:
    """Format a single order for admin panel display."""
    # Get user handle
    user_data = order.get("users") or {}
    username = user_data.get("username") or user_data.get("first_name", "Unknown")
    user_handle = f"@{username}" if username != "Unknown" else "Unknown"

    # Get product name from order_items -> products
    items = order.get("order_items", [])
    product_name = "Unknown Product"
    if items and len(items) > 0:
        # Product name is nested: order_items[0].products.name
        product_data = items[0].get("products") or {}
        product_name = product_data.get("name", "Unknown Product")
        if len(items) > 1:
            product_name += f" +{len(items) - 1}"

    created_at = order.get("created_at")

    # Fiat fields
    fiat_amount = order.get("fiat_amount")
    fiat_currency = order.get("fiat_currency")

    return {
        "id": order.get("id"),  # Full UUID for API compatibility
        "user_id": user_data.get("telegram_id"),
        "user_handle": user_handle,
        "product_name": product_name,
        "amount": float(order.get("amount", 0)),
        "fiat_amount": float(fiat_amount) if fiat_amount is not None else None,
        "fiat_currency": fiat_currency,
        "status": order.get("status", "pending"),
        "payment_method": order.get("payment_method", "unknown"),
        "source_channel": order.get("source_channel", "main"),  # main, discount, webapp
        "created_at": created_at,
    }


@router.get("/orders")
async def admin_get_orders(
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    admin=Depends(verify_admin),
):
    """Get all orders with optional filtering - formatted for admin panel."""
    db = get_database()

    query = (
        db.client.table("orders")
        .select(
            "id, status, amount, fiat_amount, fiat_currency, payment_method, payment_gateway, created_at, source_channel, "
            "users(telegram_id, username, first_name), "
            "order_items(product_id, quantity, products(name))",
        )
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
    )

    if status:
        query = query.eq("status", status)

    result = await query.execute()
    orders_data = result.data if result.data else []

    # Format orders for admin panel (matching mock data structure)
    formatted_orders = [_format_order_for_admin(order) for order in orders_data]

    return {"orders": formatted_orders}


@router.post("/orders/{order_id}/check-payment")
async def admin_check_payment(order_id: str, admin=Depends(verify_admin)):
    """Check payment status for a pending order via payment gateway API."""
    db = get_database()

    # Get order
    order_result = (
        await db.client.table("orders")
        .select("id, status, payment_id, payment_gateway, payment_method, amount")
        .eq("id", order_id)
        .single()
        .execute()
    )

    if not order_result.data:
        raise HTTPException(status_code=404, detail="Order not found")

    order = order_result.data

    if order.get("status") not in ["pending", "paid", "processing"]:
        return {
            "status": order.get("status"),
            "message": f"Order is already {order.get('status')}, no need to check payment",
        }

    payment_id = order.get("payment_id")
    payment_gateway = order.get("payment_gateway")

    if not payment_id:
        return {
            "status": order.get("status"),
            "message": "No payment_id found. Order may not have been processed for payment yet.",
        }

    # Check payment status via gateway
    if payment_gateway == "crystalpay":
        try:
            payment_service = get_payment_service()
            invoice_info = await payment_service.get_crystalpay_invoice_info(payment_id)

            state = invoice_info.get("state", "unknown")

            return {
                "order_id": order_id,
                "payment_id": payment_id,
                "gateway": payment_gateway,
                "invoice_state": state,
                "current_status": order.get("status"),
                "message": f"Invoice state: {state}",
            }
        except Exception as e:
            from core.logging import sanitize_id_for_logging

            logger.exception(
                "Failed to check CrystalPay invoice %s",
                sanitize_id_for_logging(payment_id),
            )
            return {
                "order_id": order_id,
                "payment_id": payment_id,
                "gateway": payment_gateway,
                "error": str(e),
                "message": f"Failed to check payment status: {type(e).__name__}",
            }
    else:
        return {
            "order_id": order_id,
            "payment_id": payment_id,
            "gateway": payment_gateway,
            "message": f"Manual payment check not implemented for {payment_gateway}",
        }


class ForceStatusRequest(BaseModel):
    new_status: str  # "paid", "cancelled", "processing"


@router.post("/orders/{order_id}/force-status")
async def admin_force_order_status(
    order_id: str,
    request: ForceStatusRequest,
    admin=Depends(verify_admin),
):
    """Force update order status (admin override). Use with caution."""
    db = get_database()

    valid_statuses = ["pending", "paid", "processing", "delivered", "cancelled", "refunded"]
    if request.new_status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
        )

    # Get current order
    order_result = (
        await db.client.table("orders").select("id, status").eq("id", order_id).single().execute()
    )

    if not order_result.data:
        raise HTTPException(status_code=404, detail="Order not found")

    old_status = order_result.data.get("status")

    # Update status
    result = (
        await db.client.table("orders")
        .update({"status": request.new_status})
        .eq("id", order_id)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to update order status")

    logger.warning("Admin force status change completed")

    return {
        "success": True,
        "order_id": order_id,
        "old_status": old_status,
        "new_status": request.new_status,
        "message": f"Order status updated from {old_status} to {request.new_status}",
    }


# ==================== FAQ ====================


@router.post("/faq")
async def admin_create_faq(request: CreateFAQRequest, admin=Depends(verify_admin)):
    """Create a FAQ entry."""
    db = get_database()

    result = (
        await db.client.table("faq")
        .insert(
            {
                "question": request.question,
                "answer": request.answer,
                "language_code": request.language_code,
                "category": request.category,
                "is_active": True,
            },
        )
        .execute()
    )

    if result.data:
        return {"success": True, "faq": result.data[0]}
    raise HTTPException(status_code=500, detail="Failed to create FAQ")


@router.get("/faq")
async def admin_get_faq(admin=Depends(verify_admin)):
    """Get all FAQ entries for admin."""
    db = get_database()

    result = (
        await db.client.table("faq").select("*").order("language_code").order("category").execute()
    )

    return {"faq": result.data}
