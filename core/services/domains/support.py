"""
Support Domain Service

Handles support tickets, FAQ, and refund requests.
"""
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from core.logging import get_logger

logger = get_logger(__name__)


# Refund configuration
MAX_OPEN_REFUNDS_PER_USER = 3
ALLOWED_REFUND_STATUSES = {"pending", "paid", "prepaid", "partial", "delivered"}
FORBIDDEN_REFUND_STATUSES = {"refunded", "cancelled"}

# Replacement configuration (anti-abuse)
MAX_REPLACEMENTS_PER_MONTH = 20  # Reasonable limit for legitimate cases
MAX_REPLACEMENT_TICKETS_PER_DAY = 5  # Prevent spam
MIN_HOURS_BETWEEN_REPLACEMENTS = 1  # Cooldown between replacement requests


@dataclass
class FAQEntry:
    """FAQ entry."""
    id: str
    question: str
    answer: str
    category: Optional[str] = None


@dataclass
class SupportTicket:
    """Support ticket."""
    id: str
    user_id: str
    order_id: Optional[str]
    issue_type: Optional[str]
    message: str
    status: str


class SupportService:
    """
    Support domain service.
    
    Provides clean interface for:
    - Support ticket creation
    - FAQ retrieval
    - Refund requests
    """
    
    def __init__(self, db):
        self.db = db
    
    async def create_ticket(
        self,
        user_id: str,
        message: str,
        order_id: Optional[str] = None,
        item_id: Optional[str] = None,
        issue_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a support ticket.
        
        Args:
            user_id: User database ID
            message: Issue description
            order_id: Related order ID (optional)
            item_id: Specific order item ID (optional, for item-level issues)
            issue_type: Type of issue (optional)
            
        Returns:
            Success/failure result with ticket ID
        """
        try:
            # Anti-abuse checks for replacement requests
            if issue_type == "replacement" and item_id:
                # Check 1: Has this specific item_id already been replaced?
                existing_replacement = await asyncio.to_thread(
                    lambda: self.db.client.table("tickets")
                    .select("id, status, created_at")
                    .eq("item_id", item_id)
                    .eq("issue_type", "replacement")
                    .in_("status", ["open", "approved"])
                    .order("created_at", desc=True)
                    .limit(1)
                    .execute()
                )
                
                if existing_replacement.data:
                    # Item already has an open/approved replacement ticket
                    return {
                        "success": False,
                        "reason": "This account has already been requested for replacement. Please wait for processing."
                    }
                
                # Check 2: Rate limiting - too many replacement tickets today?
                from datetime import datetime, timezone, timedelta
                today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
                
                today_count = await asyncio.to_thread(
                    lambda: self.db.client.table("tickets")
                    .select("id", count="exact")
                    .eq("user_id", user_id)
                    .eq("issue_type", "replacement")
                    .gte("created_at", today_start.isoformat())
                    .execute()
                )
                
                if (today_count.count or 0) >= MAX_REPLACEMENT_TICKETS_PER_DAY:
                    return {
                        "success": False,
                        "reason": f"Too many replacement requests today (limit: {MAX_REPLACEMENT_TICKETS_PER_DAY}). Please try again tomorrow."
                    }
                
                # Check 3: Cooldown - last replacement request was too recent?
                last_replacement = await asyncio.to_thread(
                    lambda: self.db.client.table("tickets")
                    .select("created_at")
                    .eq("user_id", user_id)
                    .eq("issue_type", "replacement")
                    .order("created_at", desc=True)
                    .limit(1)
                    .execute()
                )
                
                if last_replacement.data:
                    last_time = datetime.fromisoformat(last_replacement.data[0]["created_at"].replace("Z", "+00:00"))
                    hours_since = (datetime.now(timezone.utc) - last_time).total_seconds() / 3600
                    
                    if hours_since < MIN_HOURS_BETWEEN_REPLACEMENTS:
                        return {
                            "success": False,
                            "reason": f"Please wait {MIN_HOURS_BETWEEN_REPLACEMENTS} hour(s) between replacement requests."
                        }
                
                # Check 4: Monthly limit (but allow all items from same order)
                month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                
                monthly_count = await asyncio.to_thread(
                    lambda: self.db.client.table("tickets")
                    .select("id", count="exact")
                    .eq("user_id", user_id)
                    .eq("issue_type", "replacement")
                    .in_("status", ["open", "approved"])
                    .gte("created_at", month_start.isoformat())
                    .execute()
                )
                
                # If approaching limit, check if this is from a new order (allow if so)
                if (monthly_count.count or 0) >= MAX_REPLACEMENTS_PER_MONTH:
                    # Check if this item_id belongs to an order that already has replacement tickets
                    # If yes, allow (same order = legitimate batch issue)
                    # If no, block (new order = possible abuse)
                    if order_id:
                        order_replacements = await asyncio.to_thread(
                            lambda: self.db.client.table("tickets")
                            .select("id", count="exact")
                            .eq("user_id", user_id)
                            .eq("order_id", order_id)
                            .eq("issue_type", "replacement")
                            .in_("status", ["open", "approved"])
                            .execute()
                        )
                        # If this order already has replacement tickets, allow (batch issue)
                        if (order_replacements.count or 0) == 0:
                            return {
                                "success": False,
                                "reason": f"Monthly replacement limit reached ({MAX_REPLACEMENTS_PER_MONTH}). Contact support for assistance."
                            }
                    else:
                        return {
                            "success": False,
                            "reason": f"Monthly replacement limit reached ({MAX_REPLACEMENTS_PER_MONTH}). Contact support for assistance."
                        }
            
            ticket_data = {
                "user_id": user_id,
                "description": message,  # Use 'description' field (not 'message')
                "status": "open"
            }
            if order_id:
                ticket_data["order_id"] = order_id
            if item_id:
                ticket_data["item_id"] = item_id
            if issue_type:
                ticket_data["issue_type"] = issue_type
            
            result = await asyncio.to_thread(
                lambda: self.db.client.table("tickets").insert(ticket_data).execute()
            )
            
            if result.data:
                return {
                    "success": True,
                    "ticket_id": result.data[0].get("id"),
                    "message": "Support ticket created"
                }
            return {"success": False, "reason": "Failed to create ticket"}
        except Exception as e:
            logger.error(f"Failed to create ticket: {e}", exc_info=True)
            return {"success": False, "reason": "Database error"}
    
    async def get_faq(self, language: str = "en") -> List[FAQEntry]:
        """
        Get FAQ entries.
        
        Args:
            language: Language code
            
        Returns:
            List of FAQEntry
        """
        try:
            entries = await self.db.get_faq(language)
            return [
                FAQEntry(
                    id=e.get("id", ""),
                    question=e.get("question", ""),
                    answer=e.get("answer", ""),
                    category=e.get("category")
                )
                for e in entries
            ]
        except Exception as e:
            logger.error(f"Failed to get FAQ: {e}", exc_info=True)
            return []
    
    async def search_faq(self, question: str, language: str = "en") -> Optional[FAQEntry]:
        """
        Search FAQ for an answer.
        
        Simple keyword matching - could be enhanced with embeddings.
        
        Args:
            question: User question
            language: Language code
            
        Returns:
            FAQEntry if found, None otherwise
        """
        entries = await self.get_faq(language)
        question_lower = question.lower()
        
        for entry in entries:
            # Simple keyword matching
            if any(word in question_lower for word in entry.question.lower().split()):
                return entry
        
        return None
    
    async def request_refund(
        self,
        user_id: str,
        order_id: str,
        reason: str = ""
    ) -> Dict[str, Any]:
        """
        Request a refund for an order.
        
        Validates order status, user ownership, and refund limits.
        
        Args:
            user_id: User database ID
            order_id: Order ID
            reason: Refund reason
            
        Returns:
            Success/failure result
        """
        # Get order
        order = await self.db.get_order_by_id(order_id)
        if not order:
            return {"success": False, "reason": "Order not found"}
        
        # Validate ownership
        if order.user_id != user_id:
            return {"success": False, "reason": "Not your order"}
        
        # Check if already requested
        if order.refund_requested:
            return {"success": False, "reason": "Refund already requested"}
        
        # Validate status
        status_lower = (order.status or "").lower()
        if status_lower in FORBIDDEN_REFUND_STATUSES:
            return {"success": False, "reason": f"Refund not allowed for status '{order.status}'"}
        if status_lower not in ALLOWED_REFUND_STATUSES:
            return {"success": False, "reason": f"Refund not allowed for status '{order.status}'"}
        
        # Check refund quota
        try:
            open_count = await asyncio.to_thread(
                lambda: self.db.client.table("orders")
                .select("id", count="exact")
                .eq("user_id", user_id)
                .eq("refund_requested", True)
                .execute()
            )
            if (open_count.count or 0) >= MAX_OPEN_REFUNDS_PER_USER:
                return {"success": False, "reason": "Refund request limit reached"}
        except Exception as e:
            logger.error(f"Failed to check refund quota: {e}")
            return {"success": False, "reason": "Failed to validate refund limits"}
        
        # Create ticket and mark order
        try:
            ticket_result = await asyncio.to_thread(
                lambda: self.db.client.table("tickets").insert({
                    "user_id": user_id,
                    "order_id": order_id,
                    "issue_type": "refund",
                    "description": reason,
                    "status": "open"
                }).execute()
            )
            
            if not ticket_result.data:
                return {"success": False, "reason": "Failed to create support ticket"}
            
            await asyncio.to_thread(
                lambda: self.db.client.table("orders").update({
                    "refund_requested": True
                }).eq("id", order_id).execute()
            )
            
            return {
                "success": True,
                "message": "Refund request submitted for review",
                "ticket_id": ticket_result.data[0].get("id")
            }
        except Exception as e:
            logger.error(f"Failed to process refund request: {e}", exc_info=True)
            return {"success": False, "reason": "Failed to process refund request"}
    
    async def get_user_tickets(
        self,
        user_id: str,
        status: Optional[str] = None,
        limit: int = 20
    ) -> List[SupportTicket]:
        """
        Get user's support tickets.
        
        Args:
            user_id: User database ID
            status: Filter by status (optional)
            limit: Max results
            
        Returns:
            List of SupportTicket
        """
        try:
            query = self.db.client.table("tickets").select("*").eq("user_id", user_id)
            if status:
                query = query.eq("status", status)
            query = query.order("created_at", desc=True).limit(limit)
            
            result = await asyncio.to_thread(lambda: query.execute())
            
            return [
                SupportTicket(
                    id=t.get("id", ""),
                    user_id=t.get("user_id", ""),
                    order_id=t.get("order_id"),
                    issue_type=t.get("issue_type"),
                    message=t.get("message", t.get("description", "")),
                    status=t.get("status", "unknown")
                )
                for t in result.data or []
            ]
        except Exception as e:
            logger.error(f"Failed to get user tickets: {e}", exc_info=True)
            return []
