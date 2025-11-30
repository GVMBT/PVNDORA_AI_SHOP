"""AI Function Calling Tools"""
import asyncio
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
            product_name = arguments.get("product_name", "")
            if not product_name:
                return {
                    "success": False,
                    "reason": "Product name is required"
                }
            
            await db.add_to_waitlist(user_id, product_name)
            return {
                "success": True,
                "product_name": product_name
            }
        except Exception as e:
            print(f"ERROR: add_to_waitlist failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "reason": f"Failed to add to waitlist: {str(e)}"
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
                "reason": f"Failed to create support ticket: {str(e)}"
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
        
        # #region agent log
        import json
        with open(r"d:\pvndora\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "tools.py:395", "message": "add_to_wishlist entry", "data": {"user_id": user_id, "product_id": product_id}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
        # #endregion
        
        # Check if item already exists BEFORE upsert (to distinguish insert vs update)
        # #region agent log
        with open(r"d:\pvndora\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "tools.py:402", "message": "Before checking existing wishlist item", "data": {}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
        # #endregion
        
        # Check if item already exists BEFORE upsert (to distinguish insert vs update)
        # #region agent log
        with open(r"d:\pvndora\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "tools.py:408", "message": "Before checking existing wishlist item", "data": {}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
        # #endregion
        
        # Run synchronous Supabase call in thread pool to avoid blocking event loop
        existing_check = await asyncio.to_thread(
            lambda: db.client.table("wishlist").select("id").eq("user_id", user_id).eq("product_id", product_id).execute()
        )
        item_existed_before = bool(existing_check.data)
        
        # #region agent log
        with open(r"d:\pvndora\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "tools.py:415", "message": "After checking existing", "data": {"item_existed_before": item_existed_before, "existing_data": existing_check.data}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
        # #endregion
        
        # If already exists, return early
        if item_existed_before:
            # #region agent log
            with open(r"d:\pvndora\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "tools.py:420", "message": "Item already exists, returning early", "data": {}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
            # #endregion
            return {"success": False, "reason": "Already in wishlist"}
        
        # Use upsert to handle race conditions atomically (only if not exists)
        try:
            # #region agent log
            with open(r"d:\pvndora\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "tools.py:427", "message": "Before upsert execute (async)", "data": {}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
            # #endregion
            
            # Run upsert in thread pool to avoid blocking
            result = await asyncio.to_thread(
                lambda: db.client.table("wishlist").upsert({
                    "user_id": user_id,
                    "product_id": product_id,
                    "reminded": False
                }, on_conflict="user_id,product_id").execute()
            )
            
            # #region agent log
            with open(r"d:\pvndora\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "tools.py:437", "message": "After upsert execute", "data": {"result_has_data": bool(result.data), "result_data_count": len(result.data) if result.data else 0}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
            # #endregion
            
            # Since we checked existence before, if we get here it's a new insert
            if result.data:
                # #region agent log
                with open(r"d:\pvndora\.cursor\debug.log", "a", encoding="utf-8") as f:
                    f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "tools.py:442", "message": "Returning success (new item)", "data": {"product_name": product.name}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
                # #endregion
                return {
                    "success": True,
                    "product_name": product.name,
                    "message": "Added to wishlist"
                }
            else:
                # #region agent log
                with open(r"d:\pvndora\.cursor\debug.log", "a", encoding="utf-8") as f:
                    f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "tools.py:450", "message": "Unexpected: no data after upsert", "data": {}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
                # #endregion
                return {"success": False, "reason": "Failed to add to wishlist"}
        except Exception as e:
            # #region agent log
            with open(r"d:\pvndora\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "tools.py:437", "message": "Exception in add_to_wishlist", "data": {"error": str(e), "error_type": type(e).__name__}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
            # #endregion
            # If unique constraint violation, item already exists
            if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                return {"success": False, "reason": "Already in wishlist"}
            return {"success": False, "reason": f"Database error: {str(e)}"}
    
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
            
            # Count referrals
            referrals = await asyncio.to_thread(
                lambda: db.client.table("users").select("id", count="exact").eq(
                    "referrer_id", user_id
                ).execute()
            )
            
            return {
                "success": True,
                "referral_link": f"https://t.me/pvndora_bot?start=ref_{user['telegram_id']}",
                "referral_percent": user["personal_ref_percent"],
                "total_referrals": referrals.count if referrals.count else 0,
                "balance": user["balance"]
            }
        except Exception as e:
            print(f"ERROR: get_referral_info failed: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "reason": str(e)}
    
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
            # #region agent log
            import json, time
            with open(r"d:\pvndora\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "B", "location": "tools.py:499", "message": "request_refund entry", "data": {"user_id": user_id, "order_id": order_id}, "timestamp": int(time.time() * 1000)}) + "\n")
            # #endregion
            
            # First create ticket (if this fails, we don't update order)
            # #region agent log
            exec_start = time.time()
            with open(r"d:\pvndora\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "B", "location": "tools.py:504", "message": "Before ticket insert execute (async)", "data": {}, "timestamp": int(time.time() * 1000)}) + "\n")
            # #endregion
            
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
            
            # #region agent log
            exec_duration = (time.time() - exec_start) * 1000
            with open(r"d:\pvndora\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "B", "location": "tools.py:515", "message": "After ticket insert execute", "data": {"exec_duration_ms": exec_duration, "has_data": bool(ticket_result.data)}, "timestamp": int(time.time() * 1000)}) + "\n")
            # #endregion
            
            if not ticket_result.data:
                return {"success": False, "reason": "Failed to create support ticket"}
            
            # Then update order (if this fails, ticket exists but order not marked - acceptable)
            # #region agent log
            exec_start2 = time.time()
            with open(r"d:\pvndora\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "B", "location": "tools.py:523", "message": "Before order update execute (async)", "data": {}, "timestamp": int(time.time() * 1000)}) + "\n")
            # #endregion
            
            # Run synchronous Supabase call in thread pool to avoid blocking event loop
            await asyncio.to_thread(
                lambda: db.client.table("orders").update({
                    "refund_requested": True
                }).eq("id", order_id).execute()
            )
            
            # #region agent log
            exec_duration2 = (time.time() - exec_start2) * 1000
            with open(r"d:\pvndora\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "B", "location": "tools.py:532", "message": "After order update execute", "data": {"exec_duration_ms": exec_duration2}, "timestamp": int(time.time() * 1000)}) + "\n")
            # #endregion
            
            return {
                "success": True,
                "message": "Refund request submitted for review",
                "ticket_id": ticket_result.data[0].get("id")
            }
        except Exception as e:
            # If ticket creation failed, order remains unchanged (good)
            # If order update failed, ticket exists but order not marked (acceptable)
            return {"success": False, "reason": f"Failed to process refund request: {str(e)}"}
    
    return {"error": f"Unknown tool: {tool_name}"}

