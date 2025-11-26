"""AI Function Calling Tools"""
from typing import Dict, Any, List

# Tool definitions for Gemini function calling
TOOLS = [
    {
        "name": "check_product_availability",
        "description": "Check if a specific product is available in stock. Use this before recommending any product.",
        "parameters": {
            "type": "object",
            "properties": {
                "product_name": {
                    "type": "string",
                    "description": "Name or partial name of the product to check"
                }
            },
            "required": ["product_name"]
        }
    },
    {
        "name": "get_product_details",
        "description": "Get detailed information about a specific product including price, description, and stock status.",
        "parameters": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "string",
                    "description": "Unique ID of the product"
                }
            },
            "required": ["product_id"]
        }
    },
    {
        "name": "search_products",
        "description": "Search for products based on user requirements. Use when user describes what they need without mentioning a specific product.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query based on user's needs (e.g., 'image generation', 'code assistance', 'writing')"
                },
                "category": {
                    "type": "string",
                    "description": "Product category filter",
                    "enum": ["all", "chatgpt", "claude", "midjourney", "image", "code", "writing"]
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "create_purchase_intent",
        "description": "Create a purchase intent when user wants to buy a product. Use when user shows clear buying intent (e.g., 'I want to buy', 'давай', 'беру').",
        "parameters": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "string",
                    "description": "ID of the product to purchase"
                }
            },
            "required": ["product_id"]
        }
    },
    {
        "name": "add_to_waitlist",
        "description": "Add user to waitlist for an out-of-stock product. Use when user wants a product that is not available.",
        "parameters": {
            "type": "object",
            "properties": {
                "product_name": {
                    "type": "string",
                    "description": "Name of the product to wait for"
                }
            },
            "required": ["product_name"]
        }
    },
    {
        "name": "get_catalog",
        "description": "Get the full product catalog. Use when user asks to see all available products.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "compare_products",
        "description": "Compare two or more products. Use when user asks for comparison between services.",
        "parameters": {
            "type": "object",
            "properties": {
                "product_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of product names to compare"
                }
            },
            "required": ["product_names"]
        }
    },
    {
        "name": "create_support_ticket",
        "description": "Create a support ticket when user reports an issue with their purchase. Use when user says product doesn't work, wants replacement, or needs help.",
        "parameters": {
            "type": "object",
            "properties": {
                "issue_description": {
                    "type": "string",
                    "description": "Description of the user's issue"
                },
                "order_id": {
                    "type": "string",
                    "description": "Order ID if known (optional)"
                }
            },
            "required": ["issue_description"]
        }
    },
    {
        "name": "get_user_orders",
        "description": "Get user's recent orders. Use when user asks about their purchases or order history.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of orders to return"
                }
            }
        }
    },
    {
        "name": "get_faq_answer",
        "description": "Get answer from FAQ for common questions about payments, warranty, delivery, referral program, etc.",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "User's question to find in FAQ"
                }
            },
            "required": ["question"]
        }
    }
]


async def execute_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    user_id: str,
    db
) -> Dict[str, Any]:
    """
    Execute a tool call and return the result.
    
    Args:
        tool_name: Name of the tool to execute
        arguments: Tool arguments
        user_id: User's database ID
        db: Database instance
        
    Returns:
        Tool execution result
    """
    
    if tool_name == "check_product_availability":
        products = await db.search_products(arguments["product_name"])
        if products:
            product = products[0]
            return {
                "found": True,
                "product_id": product.id,
                "name": product.name,
                "price": product.price,
                "in_stock": product.stock_count > 0,
                "stock_count": product.stock_count
            }
        return {"found": False}
    
    elif tool_name == "get_product_details":
        product = await db.get_product_by_id(arguments["product_id"])
        if product:
            rating = await db.get_product_rating(product.id)
            return {
                "found": True,
                "id": product.id,
                "name": product.name,
                "description": product.description,
                "price": product.price,
                "type": product.type,
                "in_stock": product.stock_count > 0,
                "stock_count": product.stock_count,
                "warranty_hours": product.warranty_hours,
                "instructions": product.instructions,
                "rating": rating["average"],
                "reviews_count": rating["count"]
            }
        return {"found": False}
    
    elif tool_name == "search_products":
        query = arguments.get("query", "")
        products = await db.search_products(query)
        
        return {
            "count": len(products),
            "products": [
                {
                    "id": p.id,
                    "name": p.name,
                    "price": p.price,
                    "in_stock": p.stock_count > 0,
                    "stock_count": p.stock_count
                }
                for p in products[:5]  # Limit to 5 results
            ]
        }
    
    elif tool_name == "create_purchase_intent":
        product = await db.get_product_by_id(arguments["product_id"])
        if product and product.stock_count > 0:
            return {
                "success": True,
                "product_id": product.id,
                "product_name": product.name,
                "price": product.price,
                "action": "show_payment_button"
            }
        return {
            "success": False,
            "reason": "Product not available"
        }
    
    elif tool_name == "add_to_waitlist":
        await db.add_to_waitlist(user_id, arguments["product_name"])
        return {
            "success": True,
            "product_name": arguments["product_name"]
        }
    
    elif tool_name == "get_catalog":
        products = await db.get_products(status="active")
        return {
            "count": len(products),
            "products": [
                {
                    "id": p.id,
                    "name": p.name,
                    "price": p.price,
                    "type": p.type,
                    "in_stock": p.stock_count > 0
                }
                for p in products
            ]
        }
    
    elif tool_name == "compare_products":
        results = []
        for name in arguments.get("product_names", []):
            products = await db.search_products(name)
            if products:
                p = products[0]
                rating = await db.get_product_rating(p.id)
                results.append({
                    "name": p.name,
                    "price": p.price,
                    "type": p.type,
                    "description": p.description,
                    "in_stock": p.stock_count > 0,
                    "rating": rating["average"]
                })
        return {"products": results}
    
    elif tool_name == "create_support_ticket":
        # Create support ticket in database
        issue = arguments.get("issue_description", "")
        order_id = arguments.get("order_id")
        
        ticket_data = {
            "user_id": user_id,
            "message": issue,
            "status": "open"
        }
        if order_id:
            ticket_data["order_id"] = order_id
        
        db.client.table("tickets").insert(ticket_data).execute()
        
        return {
            "success": True,
            "message": "Support ticket created"
        }
    
    elif tool_name == "get_user_orders":
        limit = arguments.get("limit", 5)
        orders = await db.get_user_orders(user_id, limit=limit)
        
        return {
            "count": len(orders),
            "orders": [
                {
                    "id": o.id[:8],
                    "product_id": o.product_id,
                    "amount": o.amount,
                    "status": o.status,
                    "created_at": o.created_at.isoformat() if o.created_at else None,
                    "expires_at": o.expires_at.isoformat() if o.expires_at else None
                }
                for o in orders
            ]
        }
    
    elif tool_name == "get_faq_answer":
        question = arguments.get("question", "")
        faq_entries = await db.get_faq("en")  # Will use user's language in actual implementation
        
        # Simple keyword matching for FAQ
        question_lower = question.lower()
        for entry in faq_entries:
            if any(word in question_lower for word in entry.get("question", "").lower().split()):
                return {
                    "found": True,
                    "question": entry["question"],
                    "answer": entry["answer"]
                }
        
        return {"found": False}
    
    return {"error": f"Unknown tool: {tool_name}"}

