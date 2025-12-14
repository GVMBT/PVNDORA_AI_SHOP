"""Common helpers for AI tools."""
import asyncio
import re
from typing import Dict, Any, Optional, Tuple

# UUID regex pattern for validation
UUID_PATTERN = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    re.IGNORECASE
)


def is_valid_uuid(value: str) -> bool:
    """Check if string is a valid UUID."""
    return bool(UUID_PATTERN.match(value))


async def get_user_telegram_id(user_id: str, db) -> Optional[int]:
    """Get user's telegram_id from database ID."""
    result = await asyncio.to_thread(
        lambda: db.client.table("users").select("telegram_id").eq("id", user_id).execute()
    )
    return result.data[0]["telegram_id"] if result.data else None


def create_error_response(e: Exception, default_msg: str = "Operation failed.") -> Dict[str, Any]:
    """Create standardized error response, filtering technical details."""
    error_str = str(e)
    if "module" in error_str.lower() or "import" in error_str.lower() or "No module named" in error_str:
        return {"success": False, "reason": "Service temporarily unavailable. Please try again later."}
    return {"success": False, "reason": default_msg}


async def resolve_product_id(product_id_or_name: str, db) -> Tuple[Optional[str], Optional[str]]:
    """
    Resolve product ID from UUID or search by name.
    
    Args:
        product_id_or_name: Either a UUID or product name
        db: Database instance
        
    Returns:
        Tuple of (product_id, error_message)
    """
    if not product_id_or_name:
        return None, "Product ID or name is required"
    
    # If it's a valid UUID, use it directly
    if is_valid_uuid(product_id_or_name):
        return product_id_or_name, None
    
    # Otherwise, search by name
    products = await db.search_products(product_id_or_name)
    if products:
        return products[0].id, None
    
    return None, f"Product not found: {product_id_or_name}"

