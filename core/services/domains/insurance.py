"""Insurance domain service for discount channel.

Handles insurance options, replacements, and abuse prevention.
"""
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from pydantic import BaseModel

from core.logging import get_logger

logger = get_logger(__name__)


# ============================================
# Models
# ============================================

class InsuranceOption(BaseModel):
    """Insurance option for a product."""
    id: str
    product_id: Optional[str] = None  # NULL = universal option for all products
    duration_days: int
    price_percent: float  # Percentage of discount_price
    replacements_count: int
    is_active: bool
    created_at: datetime


class InsuranceReplacement(BaseModel):
    """Replacement request under insurance."""
    id: str
    order_item_id: str
    insurance_id: str
    old_stock_item_id: Optional[str] = None
    new_stock_item_id: Optional[str] = None
    reason: str
    status: str  # pending, approved, rejected, auto_approved
    rejection_reason: Optional[str] = None
    processed_by: Optional[str] = None
    processed_at: Optional[datetime] = None
    created_at: datetime


class UserRestriction(BaseModel):
    """User restriction for abuse prevention."""
    id: str
    user_id: str
    restriction_type: str  # replacement_blocked, insurance_blocked, purchase_blocked
    reason: Optional[str] = None
    expires_at: Optional[datetime] = None
    created_by: Optional[str] = None
    created_at: datetime


class ReplacementResult(BaseModel):
    """Result of a replacement request."""
    success: bool
    status: str  # auto_approved, pending_review, rejected, error
    message: str
    replacement_id: Optional[str] = None
    new_stock_item_id: Optional[str] = None
    abuse_score: int = 0


# ============================================
# Service
# ============================================

class InsuranceService:
    """Insurance operations for discount channel."""
    
    # Abuse score thresholds
    AUTO_APPROVE_THRESHOLD = 30  # Below this, auto-approve
    HOLD_FOR_REVIEW_THRESHOLD = 60  # Above this, hold for manual review
    MAX_REPLACEMENTS_PER_MONTH = 2  # Per user, across all orders
    
    def __init__(self, db_client):
        self.client = db_client
    
    # ==================== Insurance Options ====================
    
    async def get_options_for_product(self, product_id: str) -> List[InsuranceOption]:
        """Get active insurance options for a product.
        
        Returns product-specific options AND universal options (where product_id IS NULL),
        filtered to exclude insurance longer than product's duration_days.
        """
        try:
            # First, get product's duration_days to filter insurance options
            product_result = await asyncio.to_thread(
                lambda: self.client.table("products").select(
                    "duration_days"
                ).eq("id", product_id).single().execute()
            )
            
            product_duration = None
            if product_result.data:
                product_duration = product_result.data.get("duration_days")
            
            # Get product-specific options
            specific_result = await asyncio.to_thread(
                lambda: self.client.table("insurance_options").select("*").eq(
                    "product_id", product_id
                ).eq("is_active", True).execute()
            )
            
            # Get universal options (product_id IS NULL)
            universal_result = await asyncio.to_thread(
                lambda: self.client.table("insurance_options").select("*").is_(
                    "product_id", "null"
                ).eq("is_active", True).execute()
            )
            
            options = []
            
            for row in (specific_result.data or []):
                option = InsuranceOption(**row)
                # Filter: insurance duration should not exceed product duration
                if product_duration and option.duration_days > product_duration:
                    logger.debug(
                        f"Skipping insurance option {option.id}: "
                        f"{option.duration_days}d > product {product_duration}d"
                    )
                    continue
                options.append(option)
            
            for row in (universal_result.data or []):
                option = InsuranceOption(**row)
                # Filter: insurance duration should not exceed product duration
                if product_duration and option.duration_days > product_duration:
                    logger.debug(
                        f"Skipping universal insurance option {option.id}: "
                        f"{option.duration_days}d > product {product_duration}d"
                    )
                    continue
                options.append(option)
            
            # Sort by duration_days for consistent display
            options.sort(key=lambda x: x.duration_days)
            
            return options
        except Exception as e:
            logger.error(f"Failed to get insurance options: {e}")
            return []
    
    async def calculate_insurance_price(
        self, 
        product_discount_price: float, 
        insurance_option: InsuranceOption
    ) -> float:
        """Calculate insurance price based on product discount price and option percentage."""
        return round(product_discount_price * (insurance_option.price_percent / 100), 2)
    
    async def attach_insurance_to_order_item(
        self,
        order_item_id: str,
        insurance_id: str,
        delivery_date: Optional[datetime] = None
    ) -> bool:
        """Attach insurance to an order item and set expiration."""
        try:
            # Get insurance option for duration
            option_result = await asyncio.to_thread(
                lambda: self.client.table("insurance_options").select(
                    "duration_days"
                ).eq("id", insurance_id).single().execute()
            )
            
            if not option_result.data:
                logger.error(f"Insurance option {insurance_id} not found")
                return False
            
            duration_days = option_result.data["duration_days"]
            base_date = delivery_date or datetime.now(timezone.utc)
            expires_at = base_date + timedelta(days=duration_days)
            
            # Update order item
            await asyncio.to_thread(
                lambda: self.client.table("order_items").update({
                    "insurance_id": insurance_id,
                    "insurance_expires_at": expires_at.isoformat()
                }).eq("id", order_item_id).execute()
            )
            
            logger.info(f"Attached insurance {insurance_id} to order_item {order_item_id}, expires {expires_at}")
            return True
        except Exception as e:
            logger.error(f"Failed to attach insurance: {e}")
            return False
    
    # ==================== Replacements ====================
    
    async def check_insurance_valid(self, order_item_id: str) -> tuple[bool, Optional[str], int]:
        """Check if order item has valid insurance.
        
        Returns:
            (is_valid, insurance_id, remaining_replacements)
        """
        try:
            result = await asyncio.to_thread(
                lambda: self.client.table("order_items").select(
                    "insurance_id, insurance_expires_at"
                ).eq("id", order_item_id).single().execute()
            )
            
            if not result.data or not result.data.get("insurance_id"):
                return (False, None, 0)
            
            insurance_id = result.data["insurance_id"]
            expires_at_str = result.data.get("insurance_expires_at")
            
            if expires_at_str:
                expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
                if expires_at < datetime.now(timezone.utc):
                    return (False, insurance_id, 0)
            
            # Get replacements count limit
            option_result = await asyncio.to_thread(
                lambda: self.client.table("insurance_options").select(
                    "replacements_count"
                ).eq("id", insurance_id).single().execute()
            )
            
            max_replacements = option_result.data.get("replacements_count", 1) if option_result.data else 1
            
            # Count used replacements via RPC
            count_result = await asyncio.to_thread(
                lambda: self.client.rpc(
                    "count_replacements", 
                    {"p_order_item_id": order_item_id}
                ).execute()
            )
            
            used_replacements = count_result.data if count_result.data else 0
            remaining = max(0, max_replacements - used_replacements)
            
            return (remaining > 0, insurance_id, remaining)
        except Exception as e:
            logger.error(f"Failed to check insurance validity: {e}")
            return (False, None, 0)
    
    async def request_replacement(
        self,
        order_item_id: str,
        telegram_id: int,
        reason: str
    ) -> ReplacementResult:
        """Request a replacement under insurance.
        
        Flow:
        1. Check if user can request replacements (not blocked)
        2. Check if order item has valid insurance
        3. Calculate abuse score
        4. If score low -> auto-approve and deliver new item
        5. If score high -> hold for manual review
        """
        try:
            # 1. Get user and check restrictions
            user_result = await asyncio.to_thread(
                lambda: self.client.table("users").select(
                    "id"
                ).eq("telegram_id", telegram_id).single().execute()
            )
            
            if not user_result.data:
                return ReplacementResult(
                    success=False,
                    status="error",
                    message="User not found"
                )
            
            user_id = user_result.data["id"]
            
            # Check if user can request replacements via RPC
            can_request = await asyncio.to_thread(
                lambda: self.client.rpc(
                    "can_request_replacement",
                    {"p_user_id": user_id}
                ).execute()
            )
            
            if not can_request.data:
                return ReplacementResult(
                    success=False,
                    status="rejected",
                    message="Replacements are blocked for this account"
                )
            
            # Check monthly limit
            monthly_count = await self._count_monthly_replacements(telegram_id)
            if monthly_count >= self.MAX_REPLACEMENTS_PER_MONTH:
                return ReplacementResult(
                    success=False,
                    status="rejected",
                    message=f"Monthly replacement limit reached ({self.MAX_REPLACEMENTS_PER_MONTH})"
                )
            
            # 2. Check insurance validity
            is_valid, insurance_id, remaining = await self.check_insurance_valid(order_item_id)
            
            if not is_valid:
                if insurance_id:
                    return ReplacementResult(
                        success=False,
                        status="expired",
                        message="Insurance has expired or no replacements remaining"
                    )
                return ReplacementResult(
                    success=False,
                    status="no_insurance",
                    message="No insurance found for this order item"
                )
            
            # 3. Calculate abuse score
            abuse_score = await self.get_abuse_score(telegram_id)
            
            # Get old stock item
            oi_result = await asyncio.to_thread(
                lambda: self.client.table("order_items").select(
                    "stock_item_id"
                ).eq("id", order_item_id).single().execute()
            )
            
            old_stock_item_id = oi_result.data.get("stock_item_id") if oi_result.data else None
            
            # 4. Determine action based on abuse score
            if abuse_score < self.AUTO_APPROVE_THRESHOLD and monthly_count == 0:
                # Auto-approve for low-risk users with no prior replacements this month
                return await self._process_auto_approval(
                    order_item_id, insurance_id, old_stock_item_id, reason, abuse_score
                )
            else:
                # Hold for review
                return await self._create_pending_replacement(
                    order_item_id, insurance_id, old_stock_item_id, reason, abuse_score
                )
                
        except Exception as e:
            logger.error(f"Failed to process replacement request: {e}")
            return ReplacementResult(
                success=False,
                status="error",
                message=f"System error: {str(e)}"
            )
    
    async def _process_auto_approval(
        self,
        order_item_id: str,
        insurance_id: str,
        old_stock_item_id: Optional[str],
        reason: str,
        abuse_score: int
    ) -> ReplacementResult:
        """Process auto-approved replacement."""
        try:
            # Get product_id for the order item
            oi_result = await asyncio.to_thread(
                lambda: self.client.table("order_items").select(
                    "product_id"
                ).eq("id", order_item_id).single().execute()
            )
            
            if not oi_result.data:
                return ReplacementResult(
                    success=False,
                    status="error",
                    message="Order item not found",
                    abuse_score=abuse_score
                )
            
            product_id = oi_result.data["product_id"]
            
            # Find available stock item
            stock_result = await asyncio.to_thread(
                lambda: self.client.table("stock_items").select(
                    "id"
                ).eq("product_id", product_id).eq("status", "available").is_(
                    "sold_at", "null"
                ).limit(1).execute()
            )
            
            if not stock_result.data:
                # No stock available, hold for review
                return await self._create_pending_replacement(
                    order_item_id, insurance_id, old_stock_item_id, reason, abuse_score,
                    status="pending",
                    message="Awaiting stock - will be fulfilled when available"
                )
            
            new_stock_item_id = stock_result.data[0]["id"]
            
            # Create replacement record
            replacement_data = {
                "order_item_id": order_item_id,
                "insurance_id": insurance_id,
                "old_stock_item_id": old_stock_item_id,
                "new_stock_item_id": new_stock_item_id,
                "reason": reason,
                "status": "auto_approved",
                "processed_at": datetime.now(timezone.utc).isoformat()
            }
            
            result = await asyncio.to_thread(
                lambda: self.client.table("insurance_replacements").insert(
                    replacement_data
                ).execute()
            )
            
            if not result.data:
                return ReplacementResult(
                    success=False,
                    status="error",
                    message="Failed to create replacement record",
                    abuse_score=abuse_score
                )
            
            replacement_id = result.data[0]["id"]
            
            # Update order item with new stock item
            await asyncio.to_thread(
                lambda: self.client.table("order_items").update({
                    "stock_item_id": new_stock_item_id
                }).eq("id", order_item_id).execute()
            )
            
            # Mark new stock item as sold
            await asyncio.to_thread(
                lambda: self.client.table("stock_items").update({
                    "status": "sold",
                    "sold_at": datetime.now(timezone.utc).isoformat()
                }).eq("id", new_stock_item_id).execute()
            )
            
            logger.info(f"Auto-approved replacement {replacement_id} for order_item {order_item_id}")
            
            return ReplacementResult(
                success=True,
                status="auto_approved",
                message="Replacement approved automatically",
                replacement_id=replacement_id,
                new_stock_item_id=new_stock_item_id,
                abuse_score=abuse_score
            )
            
        except Exception as e:
            logger.error(f"Failed to process auto-approval: {e}")
            return ReplacementResult(
                success=False,
                status="error",
                message=str(e),
                abuse_score=abuse_score
            )
    
    async def _create_pending_replacement(
        self,
        order_item_id: str,
        insurance_id: str,
        old_stock_item_id: Optional[str],
        reason: str,
        abuse_score: int,
        status: str = "pending",
        message: str = "Request submitted for review"
    ) -> ReplacementResult:
        """Create pending replacement for manual review."""
        try:
            replacement_data = {
                "order_item_id": order_item_id,
                "insurance_id": insurance_id,
                "old_stock_item_id": old_stock_item_id,
                "reason": reason,
                "status": status
            }
            
            result = await asyncio.to_thread(
                lambda: self.client.table("insurance_replacements").insert(
                    replacement_data
                ).execute()
            )
            
            if not result.data:
                return ReplacementResult(
                    success=False,
                    status="error",
                    message="Failed to create replacement record",
                    abuse_score=abuse_score
                )
            
            replacement_id = result.data[0]["id"]
            
            logger.info(f"Created pending replacement {replacement_id} (abuse_score={abuse_score})")
            
            return ReplacementResult(
                success=True,
                status="pending_review",
                message=message,
                replacement_id=replacement_id,
                abuse_score=abuse_score
            )
            
        except Exception as e:
            logger.error(f"Failed to create pending replacement: {e}")
            return ReplacementResult(
                success=False,
                status="error",
                message=str(e),
                abuse_score=abuse_score
            )
    
    async def _count_monthly_replacements(self, telegram_id: int) -> int:
        """Count user's replacements in the last 30 days."""
        try:
            thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
            
            result = await asyncio.to_thread(
                lambda: self.client.table("insurance_replacements").select(
                    "id", count="exact"
                ).eq("status", "approved").gte(
                    "created_at", thirty_days_ago
                ).execute()
            )
            
            # Also count auto_approved
            result2 = await asyncio.to_thread(
                lambda: self.client.table("insurance_replacements").select(
                    "id", count="exact"
                ).eq("status", "auto_approved").gte(
                    "created_at", thirty_days_ago
                ).execute()
            )
            
            count1 = result.count if result.count else 0
            count2 = result2.count if result2.count else 0
            
            return count1 + count2
        except Exception as e:
            logger.error(f"Failed to count monthly replacements: {e}")
            return 0
    
    # ==================== Abuse Prevention ====================
    
    async def get_abuse_score(self, telegram_id: int) -> int:
        """Get abuse risk score for a user (0-100)."""
        try:
            result = await asyncio.to_thread(
                lambda: self.client.rpc(
                    "get_user_abuse_score",
                    {"p_telegram_id": telegram_id}
                ).execute()
            )
            
            return result.data if result.data else 0
        except Exception as e:
            logger.error(f"Failed to get abuse score: {e}")
            return 50  # Return moderate score on error
    
    async def add_user_restriction(
        self,
        user_id: str,
        restriction_type: str,
        reason: str,
        expires_at: Optional[datetime] = None,
        created_by: Optional[str] = None
    ) -> bool:
        """Add a restriction to a user."""
        try:
            data = {
                "user_id": user_id,
                "restriction_type": restriction_type,
                "reason": reason,
            }
            
            if expires_at:
                data["expires_at"] = expires_at.isoformat()
            if created_by:
                data["created_by"] = created_by
            
            await asyncio.to_thread(
                lambda: self.client.table("user_restrictions").insert(data).execute()
            )
            
            logger.info(f"Added restriction {restriction_type} to user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to add restriction: {e}")
            return False
    
    async def remove_user_restriction(
        self,
        user_id: str,
        restriction_type: str
    ) -> bool:
        """Remove a restriction from a user."""
        try:
            await asyncio.to_thread(
                lambda: self.client.table("user_restrictions").delete().eq(
                    "user_id", user_id
                ).eq("restriction_type", restriction_type).execute()
            )
            
            logger.info(f"Removed restriction {restriction_type} from user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove restriction: {e}")
            return False
    
    async def get_user_restrictions(self, user_id: str) -> List[UserRestriction]:
        """Get all active restrictions for a user."""
        try:
            now = datetime.now(timezone.utc).isoformat()
            
            result = await asyncio.to_thread(
                lambda: self.client.table("user_restrictions").select("*").eq(
                    "user_id", user_id
                ).or_(f"expires_at.is.null,expires_at.gt.{now}").execute()
            )
            
            return [UserRestriction(**row) for row in (result.data or [])]
        except Exception as e:
            logger.error(f"Failed to get restrictions: {e}")
            return []
    
    # ==================== Admin Operations ====================
    
    async def get_pending_replacements(self, limit: int = 50) -> List[InsuranceReplacement]:
        """Get pending replacement requests for admin review."""
        try:
            result = await asyncio.to_thread(
                lambda: self.client.table("insurance_replacements").select(
                    "*"
                ).eq("status", "pending").order(
                    "created_at", desc=False
                ).limit(limit).execute()
            )
            
            return [InsuranceReplacement(**row) for row in (result.data or [])]
        except Exception as e:
            logger.error(f"Failed to get pending replacements: {e}")
            return []
    
    async def approve_replacement(
        self,
        replacement_id: str,
        admin_user_id: str,
        new_stock_item_id: Optional[str] = None
    ) -> bool:
        """Approve a pending replacement."""
        try:
            # Get replacement details
            repl_result = await asyncio.to_thread(
                lambda: self.client.table("insurance_replacements").select(
                    "order_item_id"
                ).eq("id", replacement_id).single().execute()
            )
            
            if not repl_result.data:
                return False
            
            order_item_id = repl_result.data["order_item_id"]
            
            # If no stock item provided, find one
            if not new_stock_item_id:
                oi_result = await asyncio.to_thread(
                    lambda: self.client.table("order_items").select(
                        "product_id"
                    ).eq("id", order_item_id).single().execute()
                )
                
                if oi_result.data:
                    stock_result = await asyncio.to_thread(
                        lambda: self.client.table("stock_items").select(
                            "id"
                        ).eq("product_id", oi_result.data["product_id"]).eq(
                            "status", "available"
                        ).is_("sold_at", "null").limit(1).execute()
                    )
                    
                    if stock_result.data:
                        new_stock_item_id = stock_result.data[0]["id"]
            
            # Update replacement record
            update_data = {
                "status": "approved",
                "processed_by": admin_user_id,
                "processed_at": datetime.now(timezone.utc).isoformat()
            }
            
            if new_stock_item_id:
                update_data["new_stock_item_id"] = new_stock_item_id
            
            await asyncio.to_thread(
                lambda: self.client.table("insurance_replacements").update(
                    update_data
                ).eq("id", replacement_id).execute()
            )
            
            # Update order item if we have a new stock item
            if new_stock_item_id:
                await asyncio.to_thread(
                    lambda: self.client.table("order_items").update({
                        "stock_item_id": new_stock_item_id
                    }).eq("id", order_item_id).execute()
                )
                
                # Mark stock item as sold
                await asyncio.to_thread(
                    lambda: self.client.table("stock_items").update({
                        "status": "sold",
                        "sold_at": datetime.now(timezone.utc).isoformat()
                    }).eq("id", new_stock_item_id).execute()
                )
            
            logger.info(f"Approved replacement {replacement_id} by admin {admin_user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to approve replacement: {e}")
            return False
    
    async def reject_replacement(
        self,
        replacement_id: str,
        admin_user_id: str,
        rejection_reason: str
    ) -> bool:
        """Reject a pending replacement."""
        try:
            await asyncio.to_thread(
                lambda: self.client.table("insurance_replacements").update({
                    "status": "rejected",
                    "rejection_reason": rejection_reason,
                    "processed_by": admin_user_id,
                    "processed_at": datetime.now(timezone.utc).isoformat()
                }).eq("id", replacement_id).execute()
            )
            
            logger.info(f"Rejected replacement {replacement_id} by admin {admin_user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to reject replacement: {e}")
            return False
