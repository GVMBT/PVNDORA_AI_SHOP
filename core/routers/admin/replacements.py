"""Admin API for replacement moderation and user restrictions.
All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from core.logging import get_logger
from core.services.database import get_database
from core.services.domains import InsuranceService

logger = get_logger(__name__)

router = APIRouter(prefix="/replacements", tags=["admin-replacements"])

# Constants (avoid string duplication)
ADMIN_USER_UUID_DESC = "Admin user UUID"

# ============================================
# Models
# ============================================


class ReplacementResponse(BaseModel):
    id: str
    order_item_id: str
    insurance_id: str
    old_stock_item_id: str | None = None
    new_stock_item_id: str | None = None
    reason: str
    status: str
    rejection_reason: str | None = None
    processed_by: str | None = None
    processed_at: datetime | None = None
    created_at: datetime
    # Extended info
    user_telegram_id: int | None = None
    user_abuse_score: int | None = None
    product_name: str | None = None
    order_id: str | None = None


class ApproveRequest(BaseModel):
    new_stock_item_id: str | None = None


class RejectRequest(BaseModel):
    reason: str


class RestrictionCreate(BaseModel):
    user_id: str
    restriction_type: str  # replacement_blocked, insurance_blocked, purchase_blocked
    reason: str
    expires_days: int | None = None  # None = permanent


class RestrictionResponse(BaseModel):
    id: str
    user_id: str
    restriction_type: str
    reason: str | None = None
    expires_at: datetime | None = None
    created_by: str | None = None
    created_at: datetime


class AbuseStatsResponse(BaseModel):
    telegram_id: int
    abuse_score: int
    total_orders: int
    total_replacements: int
    replacement_rate: float
    account_age_days: int
    restrictions: list[RestrictionResponse]


# ============================================
# Helper Functions (reduce cognitive complexity)
# ============================================


def extract_telegram_id(row: dict) -> int | None:
    """Extract telegram_id from row data (reduces cognitive complexity)."""
    if row.get("order_items") and row["order_items"].get("orders"):
        return row["order_items"]["orders"].get("user_telegram_id")
    return None


def extract_product_name(row: dict) -> str | None:
    """Extract product_name from row data (reduces cognitive complexity)."""
    if row.get("order_items") and row["order_items"].get("products"):
        return row["order_items"]["products"].get("name")
    return None


def extract_order_id(row: dict) -> str | None:
    """Extract order_id from row data (reduces cognitive complexity)."""
    if row.get("order_items"):
        return row["order_items"].get("order_id")
    return None


async def get_abuse_score(db_client, telegram_id: int | None) -> int:
    """Get abuse score for user (reduces cognitive complexity)."""
    if not telegram_id:
        return 0
    score_result = await db_client.rpc(
        "get_user_abuse_score", {"p_telegram_id": telegram_id}
    ).execute()
    return score_result.data if score_result.data else 0


# ============================================
# Endpoints
# ============================================


@router.get("/pending", response_model=list[ReplacementResponse])
async def get_pending_replacements(limit: int = Query(50, ge=1, le=100)):
    """Get pending replacement requests for moderation."""
    db = get_database()

    try:
        result = (
            await db.client.table("insurance_replacements")
            .select(
                "*, order_items(order_id, products(name)), orders!order_items(user_telegram_id)"
            )
            .eq("status", "pending")
            .order("created_at", desc=False)
            .limit(limit)
            .execute()
        )

        replacements = []
        for row in result.data or []:
            telegram_id = extract_telegram_id(row)
            abuse_score = await get_abuse_score(db.client, telegram_id)
            product_name = extract_product_name(row)
            order_id = extract_order_id(row)

            replacements.append(
                ReplacementResponse(
                    id=row["id"],
                    order_item_id=row["order_item_id"],
                    insurance_id=row["insurance_id"],
                    old_stock_item_id=row.get("old_stock_item_id"),
                    new_stock_item_id=row.get("new_stock_item_id"),
                    reason=row["reason"],
                    status=row["status"],
                    rejection_reason=row.get("rejection_reason"),
                    processed_by=row.get("processed_by"),
                    processed_at=row.get("processed_at"),
                    created_at=row["created_at"],
                    user_telegram_id=telegram_id,
                    user_abuse_score=abuse_score,
                    product_name=product_name,
                    order_id=order_id,
                )
            )

        return replacements

    except Exception as e:
        logger.exception("Failed to get pending replacements")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{replacement_id}/approve")
async def approve_replacement(
    replacement_id: str,
    request: ApproveRequest,
    admin_user_id: str = Query(..., description=ADMIN_USER_UUID_DESC),
):
    """Approve a pending replacement."""
    db = get_database()
    insurance_service = InsuranceService(db.client)

    success = await insurance_service.approve_replacement(
        replacement_id=replacement_id,
        admin_user_id=admin_user_id,
        new_stock_item_id=request.new_stock_item_id,
    )

    if not success:
        raise HTTPException(status_code=400, detail="Failed to approve replacement")

    return {"success": True, "replacement_id": replacement_id}


@router.post("/{replacement_id}/reject")
async def reject_replacement(
    replacement_id: str,
    request: RejectRequest,
    admin_user_id: str = Query(..., description=ADMIN_USER_UUID_DESC),
):
    """Reject a pending replacement."""
    db = get_database()
    insurance_service = InsuranceService(db.client)

    success = await insurance_service.reject_replacement(
        replacement_id=replacement_id, admin_user_id=admin_user_id, rejection_reason=request.reason
    )

    if not success:
        raise HTTPException(status_code=400, detail="Failed to reject replacement")

    return {"success": True, "replacement_id": replacement_id}


# ============================================
# User Restrictions
# ============================================


@router.get("/restrictions/{user_id}", response_model=list[RestrictionResponse])
async def get_user_restrictions(user_id: str):
    """Get all active restrictions for a user."""
    db = get_database()
    insurance_service = InsuranceService(db.client)

    restrictions = await insurance_service.get_user_restrictions(user_id)

    return [
        RestrictionResponse(
            id=r.id,
            user_id=r.user_id,
            restriction_type=r.restriction_type,
            reason=r.reason,
            expires_at=r.expires_at,
            created_by=r.created_by,
            created_at=r.created_at,
        )
        for r in restrictions
    ]


@router.post("/restrictions", response_model=RestrictionResponse)
async def add_user_restriction(
    request: RestrictionCreate, admin_user_id: str = Query(..., description="Admin user UUID")
):
    """Add a restriction to a user."""
    db = get_database()
    insurance_service = InsuranceService(db.client)

    expires_at = None
    if request.expires_days:
        expires_at = datetime.now(UTC) + timedelta(days=request.expires_days)

    success = await insurance_service.add_user_restriction(
        user_id=request.user_id,
        restriction_type=request.restriction_type,
        reason=request.reason,
        expires_at=expires_at,
        created_by=admin_user_id,
    )

    if not success:
        raise HTTPException(status_code=400, detail="Failed to add restriction")

    # Fetch the created restriction
    restrictions = await insurance_service.get_user_restrictions(request.user_id)
    for r in restrictions:
        if r.restriction_type == request.restriction_type:
            return RestrictionResponse(
                id=r.id,
                user_id=r.user_id,
                restriction_type=r.restriction_type,
                reason=r.reason,
                expires_at=r.expires_at,
                created_by=r.created_by,
                created_at=r.created_at,
            )

    raise HTTPException(status_code=500, detail="Restriction created but not found")


@router.delete("/restrictions/{user_id}/{restriction_type}")
async def remove_user_restriction(user_id: str, restriction_type: str):
    """Remove a restriction from a user."""
    db = get_database()
    insurance_service = InsuranceService(db.client)

    success = await insurance_service.remove_user_restriction(user_id, restriction_type)

    if not success:
        raise HTTPException(status_code=400, detail="Failed to remove restriction")

    return {"success": True}


# ============================================
# Abuse Stats
# ============================================


@router.get("/abuse-stats/{telegram_id}", response_model=AbuseStatsResponse)
async def get_abuse_stats(telegram_id: int):
    """Get abuse statistics for a user."""
    db = get_database()
    insurance_service = InsuranceService(db.client)

    try:
        # Get abuse score
        score_result = await db.client.rpc(
            "get_user_abuse_score", {"p_telegram_id": telegram_id}
        ).execute()
        abuse_score = score_result.data if score_result.data else 0

        # Get user info
        user_result = (
            await db.client.table("users")
            .select("id, created_at")
            .eq("telegram_id", telegram_id)
            .single()
            .execute()
        )

        if not user_result.data:
            raise HTTPException(status_code=404, detail="User not found")

        user_id = user_result.data["id"]
        created_at = datetime.fromisoformat(user_result.data["created_at"].replace("Z", "+00:00"))
        account_age_days = (datetime.now(UTC) - created_at).days

        # Count orders
        orders_result = (
            await db.client.table("orders")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .eq("status", "delivered")
            .execute()
        )
        total_orders = orders_result.count if orders_result.count else 0

        # Count replacements (last 30 days)
        thirty_days_ago = (datetime.now(UTC) - timedelta(days=30)).isoformat()
        replacements_result = (
            await db.client.table("insurance_replacements")
            .select("id", count="exact")
            .gte("created_at", thirty_days_ago)
            .in_("status", ["approved", "auto_approved"])
            .execute()
        )
        total_replacements = replacements_result.count if replacements_result.count else 0

        replacement_rate = total_replacements / max(total_orders, 1)

        # Get restrictions
        restrictions = await insurance_service.get_user_restrictions(user_id)

        return AbuseStatsResponse(
            telegram_id=telegram_id,
            abuse_score=abuse_score,
            total_orders=total_orders,
            total_replacements=total_replacements,
            replacement_rate=round(replacement_rate, 2),
            account_age_days=account_age_days,
            restrictions=[
                RestrictionResponse(
                    id=r.id,
                    user_id=r.user_id,
                    restriction_type=r.restriction_type,
                    reason=r.reason,
                    expires_at=r.expires_at,
                    created_by=r.created_by,
                    created_at=r.created_at,
                )
                for r in restrictions
            ],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get abuse stats")
        raise HTTPException(status_code=500, detail=str(e))
