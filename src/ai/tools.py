"""AI Function Calling Tools"""
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
        "description": "Get the full product catalog with ALL available products. Use when user asks to see all products, what's available, catalog, or asks 'что есть', 'что есть в наличии', 'покажи все', 'каталог', 'what do you have', 'show me everything'. ALWAYS use this when user explicitly asks about availability or wants to see all products.",
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
    },
    {
        "name": "get_user_cart",
        "description": "Get user's shopping cart with all items. Use when user asks about their cart, wants to see what's in cart, or before checkout.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "add_to_cart",
        "description": "Add a product to user's shopping cart. Automatically splits items into instant (in stock) and prepaid (on-demand) quantities. Use when user wants to add a product to cart.",
        "parameters": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "string",
                    "description": "ID of the product to add"
                },
                "quantity": {
                    "type": "integer",
                    "description": "Quantity to add (default: 1)",
                    "default": 1,
                    "minimum": 1
                }
            },
            "required": ["product_id"]
        }
    },
    {
        "name": "update_cart",
        "description": "Update shopping cart: change quantity or remove item. Use when user explicitly wants to modify their cart. NEVER use 'clear' operation before payment - cart must remain filled until payment is completed!",
        "parameters": {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "description": "Operation to perform",
                    "enum": ["update_quantity", "remove_item", "clear"]
                },
                "product_id": {
                    "type": "string",
                    "description": "Product ID (required for update_quantity and remove_item)"
                },
                "quantity": {
                    "type": "integer",
                    "description": "New quantity (required for update_quantity, minimum: 1)"
                }
            },
            "required": ["operation"]
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
            # Get product details including fulfillment info
            product_details = await db.get_product_by_id(product.id)
            fulfillment_hours = getattr(product_details, 'fulfillment_time_hours', 48) if product_details else 48
            requires_prepayment = getattr(product_details, 'requires_prepayment', False) if product_details else False
            product_status = getattr(product_details, 'status', 'active') if product_details else 'active'
            
            # Determine if product is discontinued
            is_discontinued = product_status == 'discontinued'
            
            # Can fulfill on-demand only if product is active (not discontinued)
            can_fulfill_on_demand = product_status == 'active' and not is_discontinued
            
            return {
                "found": True,
                "product_id": product.id,
                "name": product.name,
                "price": product.price,
                "in_stock": product.stock_count > 0,
                "stock_count": product.stock_count,
                "status": product_status,
                "is_discontinued": is_discontinued,
                "can_fulfill_on_demand": can_fulfill_on_demand,
                "fulfillment_time_hours": fulfillment_hours if can_fulfill_on_demand else None,
                "requires_prepayment": requires_prepayment
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
        category = arguments.get("category", "all")
        
        # Use RAG for semantic search (if available)
        try:
            from core.rag import ProductSearch, VECS_AVAILABLE
            if not VECS_AVAILABLE or ProductSearch is None:
                raise ImportError("RAG not available - vecs not installed")
            
            product_search = ProductSearch()
            
            # Build filters based on category
            filters = {"status": {"$eq": "active"}}
            if category != "all":
                # Map category to product type
                category_map = {
                    "chatgpt": "shared",
                    "claude": "shared",
                    "midjourney": "shared",
                    "image": "shared",
                    "code": "key",
                    "writing": "shared"
                }
                if category in category_map:
                    filters["type"] = {"$eq": category_map[category]}
            
            # Semantic search via RAG
            rag_results = await product_search.search(query, limit=5, filters=filters)
            
            # Get full product details from DB
            products = []
            
            for result in rag_results:
                product = await db.get_product_by_id(result["product_id"])
                if product:
                    products.append({
                        "id": product.id,
                        "name": product.name,
                        "price": product.price,
                        "in_stock": product.stock_count > 0,
                        "stock_count": product.stock_count,
                        "similarity_score": result.get("score", 0.0)
                    })
            
            # If RAG didn't find enough results, fallback to text search
            if len(products) < 3:
                text_products = await db.search_products(query)
                existing_ids = {p["id"] for p in products}
                for p in text_products:
                    if p.id not in existing_ids and len(products) < 5:
                        products.append({
                            "id": p.id,
                            "name": p.name,
                            "price": p.price,
                            "in_stock": p.stock_count > 0,
                            "stock_count": p.stock_count,
                            "similarity_score": 0.0
                        })
            
            return {
                "count": len(products),
                "products": products[:5]  # Limit to 5 results
            }
        except Exception as e:
            print(f"ERROR: RAG search failed, falling back to text search: {e}")
            import traceback
            traceback.print_exc()
            # Fallback to text search
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
                    for p in products[:5]
                ]
            }
    
    elif tool_name == "create_purchase_intent":
        # Resolve product ID (supports both UUID and name search)
        product_id_or_name = arguments.get("product_id", "")
        resolved_id, error = await resolve_product_id(product_id_or_name, db)
        if error:
            return {
                "success": False,
                "reason": error
            }
        
        product = await db.get_product_by_id(resolved_id)
        if not product:
            return {
                "success": False,
                "reason": "Product not found"
            }
        
        product_status = getattr(product, 'status', 'active')
        is_discontinued = product_status == 'discontinued'
        
        # If product is discontinued, cannot create purchase intent
        if is_discontinued:
            return {
                "success": False,
                "reason": "Product is discontinued. Please use waitlist to be notified when it becomes available again."
            }
        
        if product.stock_count > 0:
            # Product in stock - instant order
            return {
                "success": True,
                "product_id": product.id,
                "product_name": product.name,
                "price": product.price,
                "order_type": "instant",
                "action": "show_payment_button"
            }
        else:
            # Product out of stock but active - prepaid order (on-demand)
            fulfillment_hours = getattr(product, 'fulfillment_time_hours', 48)
            fulfillment_days = fulfillment_hours // 24
            return {
                "success": True,
                "product_id": product.id,
                "product_name": product.name,
                "price": product.price,
                "order_type": "prepaid",
                "fulfillment_time_hours": fulfillment_hours,
                "fulfillment_days": fulfillment_days,
                "action": "show_payment_button",
                "message": f"Товар будет изготовлен под заказ за {fulfillment_days}-{fulfillment_days + 1} дня. Предоплата 100%."
            }
    
    elif tool_name == "add_to_waitlist":
        try:
            product_name = arguments.get("product_name", "").strip()
            if not product_name:
                return {
                    "success": False,
                    "reason": "Product name is required"
                }
            
            # Add to waitlist (function handles duplicates gracefully)
            await db.add_to_waitlist(user_id, product_name)
            return {
                "success": True,
                "product_name": product_name,
                "message": f"Added to waitlist for {product_name}"
            }
        except Exception as e:
            error_str = str(e)
            print(f"ERROR: add_to_waitlist failed: {error_str}")
            import traceback
            traceback.print_exc()
            
            # Check if it's a duplicate (already in waitlist) - this is not an error
            if "already" in error_str.lower() or "duplicate" in error_str.lower() or "unique" in error_str.lower():
                return {
                    "success": True,  # Not an error - user is already in waitlist
                    "product_name": product_name,
                    "message": f"You are already on the waitlist for {product_name}"
                }
            
            return {
                "success": False,
                "reason": "Failed to add to waitlist. Please try again later."
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
        try:
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
            
            # Run synchronous Supabase call in thread pool
            await asyncio.to_thread(
                lambda: db.client.table("tickets").insert(ticket_data).execute()
            )
            
            return {
                "success": True,
                "message": "Support ticket created"
            }
        except Exception as e:
            print(f"ERROR: create_support_ticket failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "reason": "Failed to create support ticket. Please try again later."
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
        # Resolve product ID (supports both UUID and name search)
        product_id_or_name = arguments.get("product_id", "")
        resolved_id, error = await resolve_product_id(product_id_or_name, db)
        if error:
            return {"success": False, "reason": error}
        
        product = await db.get_product_by_id(resolved_id)
        if not product:
            return {"success": False, "reason": "Product not found"}
        
        # Check if item already exists
        existing_check = await asyncio.to_thread(
            lambda: db.client.table("wishlist").select("id").eq("user_id", user_id).eq("product_id", resolved_id).execute()
        )
        
        if existing_check.data:
            return {"success": False, "reason": "Already in wishlist"}
        
        # Add to wishlist
        try:
            result = await asyncio.to_thread(
                lambda: db.client.table("wishlist").insert({
                    "user_id": user_id,
                    "product_id": resolved_id,
                    "reminded": False
                }).execute()
            )
            
            if result.data:
                return {
                    "success": True,
                    "product_name": product.name,
                    "message": "Added to wishlist"
                }
            return {"success": False, "reason": "Failed to add to wishlist"}
        except Exception as e:
            if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                return {"success": False, "reason": "Already in wishlist"}
            error_str = str(e)
            if "module" in error_str.lower() or "import" in error_str.lower():
                return {"success": False, "reason": "Service temporarily unavailable. Please try again later."}
            return {"success": False, "reason": "Database error. Please try again later."}
    
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
        try:
            # Get user's telegram_id for referral link
            user_result = await asyncio.to_thread(
                lambda: db.client.table("users").select(
                    "telegram_id,balance,personal_ref_percent"
                ).eq("id", user_id).execute()
            )
            
            if not user_result.data:
                return {"success": False}
            
            user = user_result.data[0]
            
            # Count Level 1 referrals (direct)
            level1_refs = await asyncio.to_thread(
                lambda: db.client.table("users").select(
                    "id", count="exact"
                ).eq("referrer_id", user_id).execute()
            )
            level1_count = level1_refs.count if level1_refs.count else 0
            
            # Count Level 2 referrals (referrals of referrals)
            level2_count = 0
            level3_count = 0
            if level1_count > 0 and level1_refs.data:
                level1_ids = [r["id"] for r in level1_refs.data]
                for l1_id in level1_ids:
                    l2_refs = await asyncio.to_thread(
                        lambda lid=l1_id: db.client.table("users").select(
                            "id", count="exact"
                        ).eq("referrer_id", lid).execute()
                    )
                    level2_count += l2_refs.count if l2_refs.count else 0
                    
                    # Count Level 3 (rarer, simplified)
                    if l2_refs.data:
                        for l2 in l2_refs.data:
                            l3_refs = await asyncio.to_thread(
                                lambda lid=l2["id"]: db.client.table("users").select(
                                    "id", count="exact"
                                ).eq("referrer_id", lid).execute()
                            )
                            level3_count += l3_refs.count if l3_refs.count else 0
            
            return {
                "success": True,
                "referral_link": f"https://t.me/pvndora_ai_bot?start=ref_{user['telegram_id']}",
                "referral_levels": {
                    "level_1": {"count": level1_count, "percent": 20},
                    "level_2": {"count": level2_count, "percent": 10},
                    "level_3": {"count": level3_count, "percent": 5}
                },
                "total_referrals": level1_count + level2_count + level3_count,
                "balance": user["balance"]
            }
        except Exception as e:
            error_str = str(e)
            print(f"ERROR: get_referral_info failed: {error_str}")
            import traceback
            traceback.print_exc()
            
            # Filter technical details
            if "module" in error_str.lower() or "import" in error_str.lower() or "No module named" in error_str:
                return {"success": False, "reason": "Service temporarily unavailable. Please try again later."}
            
            return {"success": False, "reason": "Failed to retrieve referral information. Please try again later."}
    
    elif tool_name == "get_wishlist":
        try:
            wishlist_items = await asyncio.to_thread(
                lambda: db.client.table("wishlist").select(
                    "id,product_id,products(name,price,stock_count:stock_items(count))"
                ).eq("user_id", user_id).execute()
            )
            
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
        except Exception as e:
            print(f"ERROR: get_wishlist failed: {e}")
            import traceback
            traceback.print_exc()
            return {"count": 0, "items": [], "error": str(e)}
    
    elif tool_name == "get_user_cart":
        try:
            from core.cart import get_cart_manager
            # Get user's telegram_id
            user_result = await asyncio.to_thread(
                lambda: db.client.table("users").select("telegram_id").eq("id", user_id).execute()
            )
            
            if not user_result.data:
                return {"success": False, "reason": "User not found"}
            
            telegram_id = user_result.data[0]["telegram_id"]
            cart_manager = get_cart_manager()  # Use singleton
            cart = await cart_manager.get_cart(telegram_id)
            
            if not cart:
                return {
                    "success": True,
                    "empty": True,
                    "items": [],
                    "total": 0.0
                }
            
            return {
                "success": True,
                "empty": False,
                "items": [
                    {
                        "product_id": item.product_id,
                        "product_name": item.product_name,
                        "quantity": item.quantity,
                        "instant_quantity": item.instant_quantity,
                        "prepaid_quantity": item.prepaid_quantity,
                        "unit_price": item.unit_price,
                        "discount_percent": item.discount_percent,
                        "total_price": item.total_price
                    }
                    for item in cart.items
                ],
                "instant_total": cart.instant_total,
                "prepaid_total": cart.prepaid_total,
                "subtotal": cart.subtotal,
                "total": cart.total,
                "promo_code": cart.promo_code,
                "promo_discount_percent": cart.promo_discount_percent
            }
        except Exception as e:
            error_str = str(e)
            print(f"ERROR: get_user_cart failed: {error_str}")
            import traceback
            traceback.print_exc()
            
            # Filter technical details
            if "module" in error_str.lower() or "import" in error_str.lower() or "No module named" in error_str:
                return {"success": False, "reason": "Cart service temporarily unavailable. Please try again later."}
            
            return {"success": False, "reason": "Failed to retrieve cart. Please try again later."}
    
    elif tool_name == "add_to_cart":
        try:
            from core.cart import get_cart_manager
            product_id_or_name = arguments.get("product_id", "")
            quantity = arguments.get("quantity", 1)
            
            if quantity < 1:
                return {"success": False, "reason": "Quantity must be at least 1"}
            
            # Resolve product ID (supports both UUID and name search)
            resolved_id, error = await resolve_product_id(product_id_or_name, db)
            if error:
                return {"success": False, "reason": error}
            
            product_id = resolved_id
            
            # Get product and check availability
            product = await db.get_product_by_id(product_id)
            if not product:
                return {"success": False, "reason": "Product not found"}
            
            # Get available stock with discounts
            stock_result = await asyncio.to_thread(
                lambda: db.client.table("available_stock_with_discounts").select(
                    "*"
                ).eq("product_id", product_id).limit(1).execute()
            )
            
            available_stock = len(stock_result.data) if stock_result.data else 0
            discount_percent = stock_result.data[0].get("discount_percent", 0) if stock_result.data else 0
            
            # Get user's telegram_id
            user_result = await asyncio.to_thread(
                lambda: db.client.table("users").select("telegram_id").eq("id", user_id).execute()
            )
            
            if not user_result.data:
                return {"success": False, "reason": "User not found"}
            
            telegram_id = user_result.data[0]["telegram_id"]
            cart_manager = get_cart_manager()  # Use singleton
            
            # Add to cart (auto-splits instant/prepaid)
            cart = await cart_manager.add_item(
                user_telegram_id=telegram_id,
                product_id=product_id,
                product_name=product.name,
                quantity=quantity,
                available_stock=available_stock,
                unit_price=product.price,
                discount_percent=discount_percent
            )
            
            # Find the added item
            added_item = next(
                (item for item in cart.items if item.product_id == product_id),
                None
            )
            
            return {
                "success": True,
                "product_id": product_id,
                "product_name": product.name,
                "quantity": quantity,
                "instant_quantity": added_item.instant_quantity if added_item else 0,
                "prepaid_quantity": added_item.prepaid_quantity if added_item else 0,
                "unit_price": product.price,
                "discount_percent": discount_percent,
                "cart_total": cart.total,
                "message": f"Added {product.name} to cart"
            }
        except Exception as e:
            error_str = str(e)
            print(f"ERROR: add_to_cart failed: {error_str}")
            import traceback
            traceback.print_exc()
            
            # Filter technical details
            if "module" in error_str.lower() or "import" in error_str.lower() or "No module named" in error_str:
                return {"success": False, "reason": "Cart service temporarily unavailable. Please try again later."}
            
            return {"success": False, "reason": "Failed to add item to cart. Please try again later."}
    
    elif tool_name == "update_cart":
        try:
            from core.cart import get_cart_manager
            operation = arguments.get("operation")
            product_id = arguments.get("product_id")
            quantity = arguments.get("quantity")
            
            # Get user's telegram_id
            user_result = await asyncio.to_thread(
                lambda: db.client.table("users").select("telegram_id").eq("id", user_id).execute()
            )
            
            if not user_result.data:
                return {"success": False, "reason": "User not found"}
            
            telegram_id = user_result.data[0]["telegram_id"]
            cart_manager = get_cart_manager()  # Use singleton
            
            if operation == "clear":
                await cart_manager.clear_cart(telegram_id)
                return {
                    "success": True,
                    "message": "Cart cleared",
                    "cart_total": 0.0
                }
            
            elif operation == "remove_item":
                if not product_id:
                    return {"success": False, "reason": "product_id required for remove_item"}
                
                cart = await cart_manager.remove_item(telegram_id, product_id)
                if cart:
                    return {
                        "success": True,
                        "message": "Item removed from cart",
                        "cart_total": cart.total
                    }
                return {"success": False, "reason": "Item not found in cart"}
            
            elif operation == "update_quantity":
                if not product_id or quantity is None:
                    return {"success": False, "reason": "product_id and quantity required for update_quantity"}
                
                if quantity < 0:
                    return {"success": False, "reason": "Quantity cannot be negative"}
                
                # Get product for available stock
                product = await db.get_product_by_id(product_id)
                if not product:
                    return {"success": False, "reason": "Product not found"}
                
                stock_result = await asyncio.to_thread(
                    lambda: db.client.table("available_stock_with_discounts").select(
                        "*"
                    ).eq("product_id", product_id).limit(1).execute()
                )
                available_stock = len(stock_result.data) if stock_result.data else 0
                
                if quantity == 0:
                    cart = await cart_manager.remove_item(telegram_id, product_id)
                else:
                    cart = await cart_manager.update_item_quantity(
                        telegram_id, product_id, quantity, available_stock
                    )
                
                if cart:
                    return {
                        "success": True,
                        "message": "Cart updated",
                        "cart_total": cart.total
                    }
                return {"success": False, "reason": "Cart not found or item not in cart"}
            
            else:
                return {"success": False, "reason": f"Unknown operation: {operation}"}
                
        except Exception as e:
            error_str = str(e)
            print(f"ERROR: update_cart failed: {error_str}")
            import traceback
            traceback.print_exc()
            
            # Filter technical details
            if "module" in error_str.lower() or "import" in error_str.lower() or "No module named" in error_str:
                return {"success": False, "reason": "Cart service temporarily unavailable. Please try again later."}
            
            return {"success": False, "reason": "Failed to update cart. Please try again later."}
    
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
        
        # Atomic transaction: update order and create ticket together
        try:
            # First create ticket (if this fails, we don't update order)
            # Run synchronous Supabase call in thread pool to avoid blocking event loop
            ticket_result = await asyncio.to_thread(
                lambda: db.client.table("tickets").insert({
                    "user_id": user_id,
                    "order_id": order_id,
                    "issue_type": "refund",
                    "description": reason,
                    "status": "open"
                }).execute()
            )
            
            if not ticket_result.data:
                return {"success": False, "reason": "Failed to create support ticket"}
            
            # Then update order (if this fails, ticket exists but order not marked - acceptable)
            # Run synchronous Supabase call in thread pool to avoid blocking event loop
            await asyncio.to_thread(
                lambda: db.client.table("orders").update({
                    "refund_requested": True
                }).eq("id", order_id).execute()
            )
            
            return {
                "success": True,
                "message": "Refund request submitted for review",
                "ticket_id": ticket_result.data[0].get("id")
            }
        except Exception as e:
            # If ticket creation failed, order remains unchanged (good)
            # If order update failed, ticket exists but order not marked (acceptable)
            error_str = str(e)
            # Filter technical details
            if "module" in error_str.lower() or "import" in error_str.lower() or "No module named" in error_str:
                return {"success": False, "reason": "Service temporarily unavailable. Please try again later."}
            return {"success": False, "reason": "Failed to process refund request. Please try again later."}
    
    return {"error": f"Unknown tool: {tool_name}"}

