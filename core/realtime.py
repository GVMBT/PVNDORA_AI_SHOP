"""Upstash Realtime Module - Real-time Event Broadcasting.

Emits events via Redis Streams for frontend real-time updates.
Uses existing Upstash Redis client (no additional dependencies).

Note: Using Redis Streams (XADD/XREAD) instead of Pub/Sub for better
compatibility with Upstash REST API and history/replay support.
"""

import json
from typing import Any

from core.db import get_redis
from core.logging import get_logger

logger = get_logger(__name__)


# Stream key prefixes (constants to avoid duplication)
_STREAM_PREFIX_PROFILE = "stream:realtime:profile:"
_STREAM_PREFIX_ORDERS = "stream:realtime:orders:"
_STREAM_PREFIX_ADMIN_WITHDRAWALS = "stream:realtime:admin:withdrawals"
_STREAM_PREFIX_ADMIN_ORDERS = "stream:realtime:admin:orders"
_STREAM_PREFIX_ADMIN_ACCOUNTING = "stream:realtime:admin:accounting"
_STREAM_PREFIX_LEADERBOARD = "stream:realtime:leaderboard"


async def emit_profile_update(user_id: str, data: dict[str, Any]) -> None:
    """Emit profile.updated event for a user.

    Args:
        user_id: User UUID
        data: Profile data (balance, turnover, etc.)
    """
    try:
        redis = get_redis()
        stream_key = f"{_STREAM_PREFIX_PROFILE}{user_id}"
        payload = {
            "event": "profile.updated",
            "user_id": user_id,
            "data": data,
        }
        await redis.xadd(stream_key, "*", {"data": json.dumps(payload)})
        logger.debug(f"Emitted profile.updated for user {user_id}")
    except Exception as e:
        logger.warning(f"Failed to emit profile.updated: {e}", exc_info=True)


async def emit_order_status_change(
    order_id: str, user_id: str, status: str, items_delivered: bool = False
) -> None:
    """Emit order.status.changed event.

    Args:
        order_id: Order UUID
        user_id: User UUID
        status: Order status (pending, paid, delivered, refunded)
        items_delivered: Whether items were delivered
    """
    try:
        redis = get_redis()
        stream_key = f"stream:realtime:orders:{user_id}"
        payload = {
            "event": "order.status.changed",
            "order_id": order_id,
            "user_id": user_id,
            "status": status,
            "items_delivered": items_delivered,
        }
        await redis.xadd(stream_key, "*", {"data": json.dumps(payload)})
        logger.debug(f"Emitted order.status.changed for order {order_id}")
    except Exception as e:
        logger.warning(f"Failed to emit order.status.changed: {e}", exc_info=True)


async def emit_admin_withdrawal_update(
    withdrawal_id: str, status: str, user_id: str | None = None
) -> None:
    """Emit admin.withdrawal.updated event (broadcast to all admins).

    Args:
        withdrawal_id: Withdrawal request UUID
        status: Withdrawal status (pending, approved, rejected)
        user_id: User UUID (optional, for user-specific updates)
    """
    try:
        redis = get_redis()
        # Broadcast to all admins
        stream_key = _STREAM_PREFIX_ADMIN_WITHDRAWALS
        payload = {
            "event": "admin.withdrawal.updated",
            "withdrawal_id": withdrawal_id,
            "status": status,
            "user_id": user_id,
        }
        await redis.xadd(stream_key, "*", {"data": json.dumps(payload)})

        # Also send to user if provided
        if user_id:
            user_stream_key = f"stream:realtime:profile:{user_id}"
            await redis.xadd(user_stream_key, "*", {"data": json.dumps(payload)})

        logger.debug(f"Emitted admin.withdrawal.updated for withdrawal {withdrawal_id}")
    except Exception as e:
        logger.warning(f"Failed to emit admin.withdrawal.updated: {e}", exc_info=True)


async def emit_admin_order_created(order_id: str, user_id: str, total_amount: float) -> None:
    """Emit admin.order.created event (broadcast to all admins).

    Args:
        order_id: Order UUID
        user_id: User UUID
        total_amount: Order total amount
    """
    try:
        redis = get_redis()
        stream_key = _STREAM_PREFIX_ADMIN_ORDERS
        payload = {
            "event": "admin.order.created",
            "order_id": order_id,
            "user_id": user_id,
            "total_amount": total_amount,
        }
        await redis.xadd(stream_key, "*", {"data": json.dumps(payload)})
        logger.debug(f"Emitted admin.order.created for order {order_id}")
    except Exception as e:
        logger.warning(f"Failed to emit admin.order.created: {e}", exc_info=True)


async def emit_leaderboard_update(user_id: str, new_rank: int | None = None) -> None:
    """Emit leaderboard.updated event (broadcast to all users).

    Args:
        user_id: User UUID whose ranking changed
        new_rank: New rank position (optional)
    """
    try:
        redis = get_redis()
        stream_key = _STREAM_PREFIX_LEADERBOARD
        payload = {
            "event": "leaderboard.updated",
            "user_id": user_id,
            "new_rank": new_rank,
        }
        await redis.xadd(stream_key, "*", {"data": json.dumps(payload)})
        logger.debug(f"Emitted leaderboard.updated for user {user_id}")
    except Exception as e:
        logger.warning(f"Failed to emit leaderboard.updated: {e}", exc_info=True)


async def emit_admin_accounting_update(
    change_type: str, order_id: str | None = None, expense_id: str | None = None
) -> None:
    """Emit admin.accounting.updated event (broadcast to all admins).

    Args:
        change_type: Type of change (order_expenses_created, expense_created, cashback_updated)
        order_id: Order UUID (optional)
        expense_id: Expense UUID (optional)
    """
    try:
        redis = get_redis()
        stream_key = _STREAM_PREFIX_ADMIN_ACCOUNTING
        payload = {
            "event": "admin.accounting.updated",
            "change_type": change_type,
            "order_id": order_id,
            "expense_id": expense_id,
        }
        await redis.xadd(stream_key, "*", {"data": json.dumps(payload)})
        logger.debug(f"Emitted admin.accounting.updated: {change_type}")
    except Exception as e:
        logger.warning(f"Failed to emit admin.accounting.updated: {e}", exc_info=True)
