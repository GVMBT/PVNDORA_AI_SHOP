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
    },
    {
        "name": "add_to_wishlist",
        "description": "Add a product to user's wishlist for later purchase. Use when user says 'save for later', 'add to favorites', 'bookmark'.",
        "parameters": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "string",
                    "description": "ID of the product to add to wishlist"
                }
            },
            "required": ["product_id"]
        }
    },
    {
        "name": "apply_promo_code",
        "description": "Check and apply a promo code for discount. Use when user mentions a promo code or asks about discounts.",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "The promo code to apply"
                }
            },
            "required": ["code"]
        }
    },
    {
        "name": "get_referral_info",
        "description": "Get user's referral link and statistics. Use when user asks about referral program, earning money, or inviting friends.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_wishlist",
        "description": "Get user's wishlist with saved products. Use when user asks to see their saved/favorite items.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "request_refund",
        "description": "Request a refund for a problematic order. Use when user explicitly asks for money back or refund.",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "The order ID to refund"
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for refund request"
                }
            },
            "required": ["order_id", "reason"]
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
    
    elif tool_name == "add_to_wishlist":
        product_id = arguments.get("product_id")
        product = await db.get_product_by_id(product_id)
        
        if not product:
            return {"success": False, "reason": "Product not found"}
        
        # Check if already in wishlist
        existing = db.client.table("wishlist").select("id").eq(
            "user_id", user_id
        ).eq("product_id", product_id).execute()
        
        if existing.data:
            return {"success": False, "reason": "Already in wishlist"}
        
        db.client.table("wishlist").insert({
            "user_id": user_id,
            "product_id": product_id
        }).execute()
        
        return {
            "success": True,
            "product_name": product.name
        }
    
    elif tool_name == "apply_promo_code":
        code = arguments.get("code", "").strip().upper()
        promo = await db.validate_promo_code(code)
        
        if promo:
            return {
                "valid": True,
                "code": code,
                "discount_percent": promo["discount_percent"],
                "message": f"Promo code applied! {promo['discount_percent']}% discount"
            }
        return {
            "valid": False,
            "message": "Invalid or expired promo code"
        }
    
    elif tool_name == "get_referral_info":
        # Get user's telegram_id for referral link
        user_result = db.client.table("users").select(
            "telegram_id,balance,personal_ref_percent"
        ).eq("id", user_id).execute()
        
        if not user_result.data:
            return {"success": False}
        
        user = user_result.data[0]
        
        # Count referrals
        referrals = db.client.table("users").select("id", count="exact").eq(
            "referrer_id", user_id
        ).execute()
        
        return {
            "success": True,
            "referral_link": f"https://t.me/pvndora_bot?start=ref_{user['telegram_id']}",
            "referral_percent": user["personal_ref_percent"],
            "total_referrals": referrals.count if referrals.count else 0,
            "balance": user["balance"]
        }
    
    elif tool_name == "get_wishlist":
        wishlist_items = db.client.table("wishlist").select(
            "id,product_id,products(name,price,stock_count:stock_items(count))"
        ).eq("user_id", user_id).execute()
        
        return {
            "count": len(wishlist_items.data),
            "items": [
                {
                    "id": item["product_id"],
                    "name": item.get("products", {}).get("name", "Unknown"),
                    "price": item.get("products", {}).get("price", 0),
                    "in_stock": (item.get("products", {}).get("stock_count") or [{}])[0].get("count", 0) > 0
                }
                for item in wishlist_items.data
            ]
        }
    
    elif tool_name == "request_refund":
        order_id = arguments.get("order_id")
        reason = arguments.get("reason", "")
        
        # Get order
        order = await db.get_order_by_id(order_id)
        if not order:
            return {"success": False, "reason": "Order not found"}
        
        if order.user_id != user_id:
            return {"success": False, "reason": "Not your order"}
        
        if order.refund_requested:
            return {"success": False, "reason": "Refund already requested"}
        
        # Mark refund as requested
        db.client.table("orders").update({
            "refund_requested": True
        }).eq("id", order_id).execute()
        
        # Create support ticket for admin review
        db.client.table("tickets").insert({
            "user_id": user_id,
            "order_id": order_id,
            "issue_type": "refund",
            "description": reason,
            "status": "open"
        }).execute()
        
        return {
            "success": True,
            "message": "Refund request submitted for review"
        }
    
    return {"error": f"Unknown tool: {tool_name}"}

