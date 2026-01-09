"""Promo code domain service for discount channel migration.

Handles personal promo code generation and validation.
"""
import asyncio
import secrets
import string
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from pydantic import BaseModel

from core.logging import get_logger

logger = get_logger(__name__)


# ============================================
# Models
# ============================================

class PromoCode(BaseModel):
    """Promo code model."""
    id: str
    code: str
    discount_percent: int
    discount_amount: Optional[float] = None
    max_uses: Optional[int] = None
    current_uses: int = 0
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    is_active: bool = True
    # Personal promo code fields
    target_user_id: Optional[str] = None
    is_personal: bool = False
    source_trigger: Optional[str] = None
    # Product-specific promo code
    product_id: Optional[str] = None  # NULL = applies to entire cart, NOT NULL = only to this product
    created_at: datetime


class PromoValidationResult(BaseModel):
    """Result of promo code validation."""
    valid: bool
    code: Optional[str] = None
    discount_percent: int = 0
    discount_amount: Optional[float] = None
    product_id: Optional[str] = None  # NULL = cart-wide, NOT NULL = product-specific
    error_message: Optional[str] = None


# ============================================
# Trigger Types
# ============================================

class PromoTriggers:
    """Promo code trigger types for analytics."""
    ISSUE_NO_INSURANCE = "issue_no_insurance"
    INSURANCE_EXPIRED = "insurance_expired"
    REPLACEMENT_LIMIT = "replacement_limit"
    LOYAL_3_PURCHASES = "loyal_3_purchases"
    INACTIVE_7_DAYS = "inactive_7_days"
    FIRST_PVNDORA_PURCHASE = "first_pvndora_purchase"
    REFERRAL_BONUS = "referral_bonus"


# ============================================
# Service
# ============================================

class PromoCodeService:
    """Promo code operations for discount channel migration."""
    
    # Default expiration for personal promo codes
    DEFAULT_EXPIRATION_DAYS = 14
    
    def __init__(self, db_client):
        self.client = db_client
    
    # ==================== Generation ====================
    
    def _generate_code(self, prefix: str, user_identifier: str) -> str:
        """Generate a unique personal promo code.
        
        Format: PREFIX_USERID_RANDOM
        Example: MIGRATE_123456_XK7M
        """
        random_suffix = ''.join(
            secrets.choice(string.ascii_uppercase + string.digits) 
            for _ in range(4)
        )
        # Truncate user identifier if too long
        user_short = user_identifier[:10] if len(user_identifier) > 10 else user_identifier
        return f"{prefix}_{user_short}_{random_suffix}"
    
    async def generate_personal_promo(
        self,
        user_id: str,
        telegram_id: int,
        trigger: str,
        discount_percent: int = 50,
        expiration_days: Optional[int] = None
    ) -> Optional[str]:
        """Generate a personal promo code for a user.
        
        Args:
            user_id: UUID of the user
            telegram_id: Telegram ID (used in code generation)
            trigger: What triggered this promo (from PromoTriggers)
            discount_percent: Discount percentage (default 50%)
            expiration_days: Days until expiration (default 14)
            
        Returns:
            Generated promo code string or None on failure
        """
        try:
            # Determine prefix based on trigger
            prefix_map = {
                PromoTriggers.ISSUE_NO_INSURANCE: "REPLACE",
                PromoTriggers.INSURANCE_EXPIRED: "EXPIRED",
                PromoTriggers.REPLACEMENT_LIMIT: "LIMIT",
                PromoTriggers.LOYAL_3_PURCHASES: "LOYAL",
                PromoTriggers.INACTIVE_7_DAYS: "COMEBACK",
                PromoTriggers.FIRST_PVNDORA_PURCHASE: "WELCOME",
                PromoTriggers.REFERRAL_BONUS: "REFBONUS",
            }
            prefix = prefix_map.get(trigger, "PROMO")
            
            # Generate unique code
            code = self._generate_code(prefix, str(telegram_id))
            
            # Check if code already exists (unlikely but possible)
            existing = await asyncio.to_thread(
                lambda: self.client.table("promo_codes").select("id").eq("code", code).execute()
            )
            
            if existing.data:
                # Regenerate with different random suffix
                code = self._generate_code(prefix, str(telegram_id))
            
            # Calculate expiration
            days = expiration_days or self.DEFAULT_EXPIRATION_DAYS
            valid_until = datetime.now(timezone.utc) + timedelta(days=days)
            
            # Create promo code
            promo_data = {
                "code": code,
                "discount_percent": discount_percent,
                "max_uses": 1,
                "current_uses": 0,
                "valid_from": datetime.now(timezone.utc).isoformat(),
                "valid_until": valid_until.isoformat(),
                "is_active": True,
                "target_user_id": user_id,
                "is_personal": True,
                "source_trigger": trigger,
            }
            
            result = await asyncio.to_thread(
                lambda: self.client.table("promo_codes").insert(promo_data).execute()
            )
            
            if not result.data:
                logger.error(f"Failed to create promo code for user {user_id}")
                return None
            
            logger.info(f"Created personal promo {code} for user {telegram_id} (trigger={trigger})")
            return code
            
        except Exception as e:
            logger.error(f"Failed to generate personal promo: {e}")
            return None
    
    # ==================== Validation ====================
    
    async def validate_promo_code(
        self,
        code: str,
        user_id: Optional[str] = None,
        telegram_id: Optional[int] = None
    ) -> PromoValidationResult:
        """Validate a promo code for a user.
        
        For personal promo codes, checks if the user matches target_user_id.
        """
        try:
            # Fetch promo code
            result = await self.client.table("promo_codes").select("*").eq(
                "code", code.upper()
            ).eq("is_active", True).single().execute()
            
            if not result.data:
                return PromoValidationResult(
                    valid=False,
                    error_message="Promo code not found or inactive"
                )
            
            promo = result.data
            now = datetime.now(timezone.utc)
            
            # Check validity dates
            if promo.get("valid_from"):
                valid_from = datetime.fromisoformat(
                    promo["valid_from"].replace("Z", "+00:00")
                )
                if now < valid_from:
                    return PromoValidationResult(
                        valid=False,
                        error_message="Promo code is not yet active"
                    )
            
            if promo.get("valid_until"):
                valid_until = datetime.fromisoformat(
                    promo["valid_until"].replace("Z", "+00:00")
                )
                if now > valid_until:
                    return PromoValidationResult(
                        valid=False,
                        error_message="Promo code has expired"
                    )
            
            # Check usage limit
            max_uses = promo.get("max_uses")
            current_uses = promo.get("current_uses", 0)
            if max_uses and current_uses >= max_uses:
                return PromoValidationResult(
                    valid=False,
                    error_message="Promo code usage limit reached"
                )
            
            # Check personal promo code restriction
            if promo.get("is_personal") and promo.get("target_user_id"):
                target_user_id = promo["target_user_id"]
                
                # Get user_id from telegram_id if needed
                if not user_id and telegram_id:
                    user_result = await self.client.table("users").select(
                        "id"
                    ).eq("telegram_id", telegram_id).single().execute()
                    
                    if user_result.data:
                        user_id = user_result.data["id"]
                
                if not user_id or user_id != target_user_id:
                    return PromoValidationResult(
                        valid=False,
                        error_message="This promo code is for another user"
                    )
            
            return PromoValidationResult(
                valid=True,
                code=promo["code"],
                discount_percent=promo.get("discount_percent", 0),
                discount_amount=promo.get("discount_amount"),
                product_id=promo.get("product_id")  # NULL = cart-wide, NOT NULL = product-specific
            )
            
        except Exception as e:
            logger.error(f"Failed to validate promo code: {e}")
            return PromoValidationResult(
                valid=False,
                error_message="Validation error"
            )
    
    async def use_promo_code(self, code: str) -> bool:
        """Increment usage count for a promo code."""
        try:
            # Get current uses
            result = await self.client.table("promo_codes").select(
                "current_uses"
            ).eq("code", code.upper()).single().execute()
            
            if not result.data:
                return False
            
            current = result.data.get("current_uses", 0)
            
            # Increment
            await self.client.table("promo_codes").update({
                "current_uses": current + 1
            }).eq("code", code.upper()).execute()
            
            logger.info(f"Used promo code {code}, new count: {current + 1}")
            return True
        except Exception as e:
            logger.error(f"Failed to use promo code: {e}")
            return False
    
    # ==================== Queries ====================
    
    async def get_user_active_promos(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[PromoCode]:
        """Get active personal promo codes for a user."""
        try:
            now = datetime.now(timezone.utc).isoformat()
            
            result = await self.client.table("promo_codes").select("*").eq(
                "target_user_id", user_id
            ).eq("is_active", True).or_(
                f"valid_until.is.null,valid_until.gt.{now}"
            ).order("created_at", desc=True).limit(limit).execute()
            
            return [PromoCode(**row) for row in result.data]
        except Exception as e:
            logger.error(f"Failed to get user promos: {e}")
            return []
    
    async def get_promo_by_trigger(
        self,
        user_id: str,
        trigger: str
    ) -> Optional[PromoCode]:
        """Get a specific promo code by trigger type for a user."""
        try:
            result = await self.client.table("promo_codes").select("*").eq(
                "target_user_id", user_id
            ).eq("source_trigger", trigger).eq("is_active", True).order(
                "created_at", desc=True
            ).limit(1).execute()
            
            if result.data:
                return PromoCode(**result.data[0])
            return None
        except Exception as e:
            logger.error(f"Failed to get promo by trigger: {e}")
            return None
    
    async def deactivate_promo(self, promo_id: str) -> bool:
        """Deactivate a promo code."""
        try:
            await self.client.table("promo_codes").update({
                "is_active": False
            }).eq("id", promo_id).execute()
            
            logger.info(f"Deactivated promo code {promo_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to deactivate promo: {e}")
            return False
    
    # ==================== Analytics ====================
    
    async def get_promo_stats_by_trigger(self) -> dict:
        """Get usage statistics grouped by trigger type."""
        try:
            result = await self.client.table("promo_codes").select(
                "source_trigger, current_uses, is_active"
            ).not_.is_("source_trigger", "null").execute()
            
            stats = {}
            for row in result.data:
                trigger = row.get("source_trigger", "unknown")
                if trigger not in stats:
                    stats[trigger] = {"total": 0, "used": 0, "active": 0}
                
                stats[trigger]["total"] += 1
                stats[trigger]["used"] += row.get("current_uses", 0)
                if row.get("is_active"):
                    stats[trigger]["active"] += 1
            
            return stats
        except Exception as e:
            logger.error(f"Failed to get promo stats: {e}")
            return {}
