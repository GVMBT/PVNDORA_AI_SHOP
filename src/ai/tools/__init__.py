"""
AI Function Calling Tools Module

Organized into logical groups:
- product_tools: Product search, catalog, availability
- cart_tools: Shopping cart operations
- user_tools: User profile, orders, wishlist, referrals
- support_tools: FAQ, tickets, refunds

Usage:
    from src.ai.tools import TOOLS, execute_tool
"""
from typing import Dict, Any

# Import tool definitions
from .definitions import TOOLS

# Import handlers from each module
from .product_tools import PRODUCT_HANDLERS
from .cart_tools import CART_HANDLERS
from .user_tools import USER_HANDLERS
from .support_tools import SUPPORT_HANDLERS

# Combine all handlers into single dispatch table
TOOL_HANDLERS = {
    **PRODUCT_HANDLERS,
    **CART_HANDLERS,
    **USER_HANDLERS,
    **SUPPORT_HANDLERS,
}


async def execute_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    user_id: str,
    db,
    language: str = "en"
) -> Dict[str, Any]:
    """
    Execute a tool call and return the result.
    
    Uses dispatch table for clean handler routing.
    
    Args:
        tool_name: Name of the tool to execute
        arguments: Tool arguments
        user_id: User's database ID
        db: Database instance
        language: User's language code
        
    Returns:
        Tool execution result
    """
    handler = TOOL_HANDLERS.get(tool_name)
    
    if not handler:
        return {"error": f"Unknown tool: {tool_name}"}
    
    return await handler(arguments, user_id, db, language)


# Public API
__all__ = [
    "TOOLS",
    "execute_tool",
    "TOOL_HANDLERS",
]

