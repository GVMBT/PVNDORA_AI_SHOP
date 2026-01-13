"""
Admin Withdrawals Router

Withdrawal requests management endpoints.
All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from core.auth import verify_admin
from core.logging import get_logger
from core.routers.deps import get_notification_service
from core.services.database import get_database

from .models import ProcessWithdrawalRequest

logger = get_logger(__name__)

router = APIRouter(prefix="/withdrawals", tags=["admin-withdrawals"])

# Constants to avoid string duplication (S1192)
ERROR_WITHDRAWAL_NOT_FOUND = "Withdrawal request not found"

# =============================================================================
# Helper Functions (reduce cognitive complexity)
# =============================================================================


def extract_withdrawal_amounts(withdrawal: dict) -> tuple[float, str, float]:
    """Extract withdrawal amounts and currency (reduces cognitive complexity)."""
    amount_debited = float(withdrawal.get("amount_debited") or withdrawal["amount"])
    balance_currency = withdrawal.get("balance_currency") or "USD"
    amount_to_pay = float(withdrawal.get("amount_to_pay") or withdrawal["amount"])
    return amount_debited, balance_currency, amount_to_pay


def validate_withdrawal_status(withdrawal: dict, allowed_statuses: list[str]) -> None:
    """Validate withdrawal status (reduces cognitive complexity)."""
    if withdrawal["status"] not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Withdrawal request is already {withdrawal['status']}",
        )


def get_admin_id(admin) -> str:
    """Get admin ID from admin object (reduces cognitive complexity)."""
    admin_id = str(admin.id) if admin and admin.id else None
    if not admin_id:
        raise HTTPException(status_code=500, detail="Admin ID not available")
    return admin_id


def validate_user_balance(
    current_balance: float,
    amount_debited: float,
    user_currency: str,
    withdrawal_currency: str,
) -> None:
    """Validate user has sufficient balance (reduces cognitive complexity)."""
    if current_balance < amount_debited:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient balance. User has {current_balance:.2f} {user_currency}, requested {amount_debited:.2f} {withdrawal_currency}",
        )


@router.get("")
async def get_withdrawals(
    status: str = Query(
        "pending", description="Filter by status: pending, processing, completed, rejected, all"
    ),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    admin=Depends(verify_admin),
):
    """Get withdrawal requests with optional status filter."""
    db = get_database()

    try:
        query = (
            db.client.table("withdrawal_requests")
            .select(
                "*, users!withdrawal_requests_user_id_fkey(username, first_name, telegram_id, balance)"
            )
            .order("created_at", desc=True)
            .limit(limit)
            .offset(offset)
        )

        if status and status != "all":
            query = query.eq("status", status)

        result = await query.execute()

        withdrawals = []
        for w in result.data or []:
            user_data = w.pop("users", {}) or {}
            withdrawals.append(
                {
                    **w,
                    "username": user_data.get("username"),
                    "first_name": user_data.get("first_name"),
                    "telegram_id": user_data.get("telegram_id"),
                    "user_balance": user_data.get("balance", 0),
                }
            )

        return {"withdrawals": withdrawals, "count": len(withdrawals)}

    except Exception as e:
        logger.exception("Error fetching withdrawals")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{withdrawal_id}")
async def get_withdrawal(withdrawal_id: str, admin=Depends(verify_admin)):
    """Get single withdrawal request by ID."""
    db = get_database()

    try:
        result = (
            await db.client.table("withdrawal_requests")
            .select(
                "*, users!withdrawal_requests_user_id_fkey(username, first_name, telegram_id, balance)"
            )
            .eq("id", withdrawal_id)
            .single()
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail=ERROR_WITHDRAWAL_NOT_FOUND)

        withdrawal_data = result.data
        user_data = withdrawal_data.pop("users", {}) or {}
        withdrawal_data["username"] = user_data.get("username")
        withdrawal_data["first_name"] = user_data.get("first_name")
        withdrawal_data["telegram_id"] = user_data.get("telegram_id")
        withdrawal_data["user_balance"] = user_data.get("balance", 0)

        return {"withdrawal": withdrawal_data}

    except HTTPException:
        raise
    except Exception as e:
        from core.logging import sanitize_id_for_logging

        logger.exception("Error fetching withdrawal %s", sanitize_id_for_logging(withdrawal_id))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{withdrawal_id}/approve")
async def approve_withdrawal(
    withdrawal_id: str, request: ProcessWithdrawalRequest, admin=Depends(verify_admin)
):
    """
    Approve a withdrawal request and deduct balance.

    Uses snapshot pricing: amount_debited is in user's balance currency,
    amount_to_pay is fixed USDT amount to send.
    """
    db = get_database()

    try:
        # Get withdrawal request with all snapshot fields
        withdrawal_result = (
            await db.client.table("withdrawal_requests")
            .select(
                "id, user_id, amount, amount_debited, amount_to_pay, balance_currency, exchange_rate, status, payment_method, wallet_address, network_fee"
            )
            .eq("id", withdrawal_id)
            .single()
            .execute()
        )

        if not withdrawal_result.data:
            raise HTTPException(status_code=404, detail=ERROR_WITHDRAWAL_NOT_FOUND)

        withdrawal = withdrawal_result.data
        validate_withdrawal_status(withdrawal, ["pending"])

        user_id = withdrawal["user_id"]
        amount_debited, balance_currency, amount_to_pay_usdt = extract_withdrawal_amounts(
            withdrawal
        )
        payment_method = withdrawal.get("payment_method", "crypto")
        wallet_address = withdrawal.get("wallet_address", "")

        # Get user balance and telegram_id for notification
        user_result = (
            await db.client.table("users")
            .select("balance, balance_currency, telegram_id")
            .eq("id", user_id)
            .single()
            .execute()
        )

        if not user_result.data:
            raise HTTPException(status_code=404, detail="User not found")

        current_balance = float(user_result.data.get("balance", 0))
        user_balance_currency = user_result.data.get("balance_currency") or "USD"
        user_telegram_id = user_result.data.get("telegram_id")

        validate_user_balance(
            current_balance, amount_debited, user_balance_currency, balance_currency
        )
        admin_id = get_admin_id(admin)

        # Update withdrawal status to processing (balance will be deducted)
        await (
            db.client.table("withdrawal_requests")
            .update(
                {
                    "status": "processing",
                    "admin_comment": request.admin_comment,
                    "processed_by": admin_id,
                    "processed_at": datetime.now(UTC).isoformat(),
                }
            )
            .eq("id", withdrawal_id)
            .execute()
        )

        # Deduct balance (amount_debited in user's currency)
        new_balance = current_balance - amount_debited
        try:
            # Update balance directly
            await (
                db.client.table("users")
                .update({"balance": new_balance})
                .eq("id", user_id)
                .execute()
            )

            # Create withdrawal transaction with correct currency
            await (
                db.client.table("balance_transactions")
                .insert(
                    {
                        "user_id": user_id,
                        "type": "withdrawal",
                        "amount": amount_debited,  # Amount in user's currency
                        "currency": balance_currency,  # User's balance currency
                        "balance_before": current_balance,
                        "balance_after": new_balance,
                        "status": "completed",
                        "description": f"Вывод {amount_to_pay_usdt:.2f} USDT на {wallet_address[:8]}...",
                        "reference_type": "withdrawal_request",
                        "reference_id": withdrawal_id,
                        "metadata": {
                            "payment_method": payment_method,
                            "wallet_address": wallet_address,
                            "usdt_amount": amount_to_pay_usdt,
                            "exchange_rate": withdrawal.get("exchange_rate"),
                            "network_fee": withdrawal.get("network_fee"),
                        },
                    }
                )
                .execute()
            )
        except Exception:
            logger.exception(f"Failed to deduct balance for withdrawal {withdrawal_id}")
            # Rollback withdrawal status
            await (
                db.client.table("withdrawal_requests")
                .update(
                    {
                        "status": "pending",
                        "admin_comment": None,
                        "processed_by": None,
                        "processed_at": None,
                    }
                )
                .eq("id", withdrawal_id)
                .execute()
            )
            raise HTTPException(
                status_code=500,
                detail="Failed to deduct balance. Withdrawal request remains pending.",
            )

        from core.logging import sanitize_id_for_logging, sanitize_string_for_logging

        logger.info(
            "Admin %s approved withdrawal %s: %.2f %s → %.2f USDT to %s",
            sanitize_id_for_logging(admin_id),
            sanitize_id_for_logging(withdrawal_id),
            amount_debited,
            balance_currency,
            amount_to_pay_usdt,
            sanitize_string_for_logging(wallet_address, max_length=20),
        )

        # Send user notification (best-effort)
        if user_telegram_id:
            try:
                notification_service = get_notification_service()
                await notification_service.send_withdrawal_approved_notification(
                    telegram_id=user_telegram_id,
                    amount=amount_to_pay_usdt,  # Show USDT amount!
                    currency="USDT",
                    method=f"TRC20 ({wallet_address[:8]}...)",
                )
            except Exception as e:
                logger.warning(f"Failed to send withdrawal approved notification: {e}")

        return {
            "success": True,
            "withdrawal_id": withdrawal_id,
            "status": "processing",
            "message": f"Withdrawal approved. Please send {amount_to_pay_usdt:.2f} USDT to {wallet_address}",
            "amount_to_pay": amount_to_pay_usdt,
            "wallet_address": wallet_address,
        }

    except HTTPException:
        raise
    except Exception as e:
        from core.logging import sanitize_id_for_logging

        logger.error(
            "Error approving withdrawal %s: %s",
            sanitize_id_for_logging(withdrawal_id),
            type(e).__name__,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{withdrawal_id}/reject")
async def reject_withdrawal(
    withdrawal_id: str, request: ProcessWithdrawalRequest, admin=Depends(verify_admin)
):
    """
    Reject a withdrawal request.

    If status was 'processing' (balance already deducted), returns balance to user.
    Uses amount_debited for correct currency handling.
    """
    db = get_database()

    try:
        # Get withdrawal request with snapshot fields
        withdrawal_result = (
            await db.client.table("withdrawal_requests")
            .select(
                "id, status, user_id, amount, amount_debited, amount_to_pay, balance_currency, users!withdrawal_requests_user_id_fkey(telegram_id)"
            )
            .eq("id", withdrawal_id)
            .single()
            .execute()
        )

        if not withdrawal_result.data:
            raise HTTPException(status_code=404, detail=ERROR_WITHDRAWAL_NOT_FOUND)

        withdrawal = withdrawal_result.data
        validate_withdrawal_status(withdrawal, ["pending", "processing"])

        user_id = withdrawal["user_id"]
        amount_debited, balance_currency, amount_to_pay = extract_withdrawal_amounts(withdrawal)

        user_telegram_id = (
            withdrawal.get("users", {}).get("telegram_id") if withdrawal.get("users") else None
        )

        admin_id = get_admin_id(admin)

        # If status was processing, we need to return balance
        if withdrawal["status"] == "processing":
            # Return balance (in user's currency)
            await db.client.rpc(
                "add_to_user_balance",
                {
                    "p_user_id": user_id,
                    "p_amount": amount_debited,  # Return in user's currency
                    "p_reason": f"Withdrawal request {withdrawal_id[:8]} rejected",
                },
            ).execute()
            logger.info(
                f"Returned {amount_debited:.2f} {balance_currency} to user {user_id} after withdrawal rejection"
            )

        # Update withdrawal status to rejected
        await (
            db.client.table("withdrawal_requests")
            .update(
                {
                    "status": "rejected",
                    "admin_comment": request.admin_comment,
                    "processed_by": admin_id,
                    "processed_at": datetime.now(UTC).isoformat(),
                }
            )
            .eq("id", withdrawal_id)
            .execute()
        )

        logger.info(f"Admin {admin_id} rejected withdrawal {withdrawal_id}")

        # Send user notification (best-effort)
        if user_telegram_id:
            try:
                notification_service = get_notification_service()
                await notification_service.send_withdrawal_rejected_notification(
                    telegram_id=user_telegram_id,
                    amount=amount_to_pay,  # Show USDT amount user would have received
                    currency="USDT",
                    reason=request.admin_comment or "Заявка отклонена администратором",
                )
            except Exception as e:
                logger.warning(f"Failed to send withdrawal rejected notification: {e}")

        return {
            "success": True,
            "withdrawal_id": withdrawal_id,
            "status": "rejected",
            "message": "Withdrawal request rejected",
        }

    except HTTPException:
        raise
    except Exception as e:
        from core.logging import sanitize_id_for_logging

        logger.error(
            "Error rejecting withdrawal %s: %s",
            sanitize_id_for_logging(withdrawal_id),
            type(e).__name__,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{withdrawal_id}/complete")
async def complete_withdrawal(
    withdrawal_id: str, request: ProcessWithdrawalRequest, admin=Depends(verify_admin)
):
    """Mark withdrawal as completed (funds sent)."""
    db = get_database()

    try:
        # Get withdrawal request with user info for notification
        withdrawal_result = (
            await db.client.table("withdrawal_requests")
            .select(
                "id, status, amount, amount_to_pay, payment_method, users!withdrawal_requests_user_id_fkey(telegram_id)"
            )
            .eq("id", withdrawal_id)
            .single()
            .execute()
        )

        if not withdrawal_result.data:
            raise HTTPException(status_code=404, detail=ERROR_WITHDRAWAL_NOT_FOUND)

        withdrawal = withdrawal_result.data
        if withdrawal["status"] != "processing":
            raise HTTPException(
                status_code=400,
                detail=f"Withdrawal must be in 'processing' status to be completed. Current status: {withdrawal['status']}",
            )

        # Use amount_to_pay (USDT) if available, else legacy amount
        amount_to_pay = float(withdrawal.get("amount_to_pay") or withdrawal["amount"])
        payment_method = withdrawal.get("payment_method", "unknown")
        user_telegram_id = (
            withdrawal.get("users", {}).get("telegram_id") if withdrawal.get("users") else None
        )

        admin_id = str(admin.id) if admin and admin.id else None
        if not admin_id:
            raise HTTPException(status_code=500, detail="Admin ID not available")

        # Update withdrawal status to completed
        await (
            db.client.table("withdrawal_requests")
            .update(
                {
                    "status": "completed",
                    "admin_comment": request.admin_comment,
                    "processed_by": admin_id,
                    "processed_at": datetime.now(UTC).isoformat(),
                }
            )
            .eq("id", withdrawal_id)
            .execute()
        )

        from core.logging import sanitize_id_for_logging

        logger.info(
            "Admin %s marked withdrawal %s as completed",
            sanitize_id_for_logging(admin_id),
            sanitize_id_for_logging(withdrawal_id),
        )

        # Send user notification (best-effort)
        if user_telegram_id:
            try:
                notification_service = get_notification_service()
                await notification_service.send_withdrawal_completed_notification(
                    telegram_id=user_telegram_id,
                    amount=amount_to_pay,
                    currency="USDT",
                    method=payment_method,
                )
            except Exception as e:
                logger.warning(f"Failed to send withdrawal completed notification: {e}")

        return {
            "success": True,
            "withdrawal_id": withdrawal_id,
            "status": "completed",
            "message": "Withdrawal marked as completed",
        }

    except HTTPException:
        raise
    except Exception as e:
        from core.logging import sanitize_id_for_logging

        logger.error(
            "Error completing withdrawal %s: %s",
            sanitize_id_for_logging(withdrawal_id),
            type(e).__name__,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))
