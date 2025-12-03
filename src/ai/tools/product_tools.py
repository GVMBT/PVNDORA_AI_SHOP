"""Product-related tool handlers."""
from typing import Dict, Any

from .helpers import resolve_product_id


async def handle_check_product_availability(
    arguments: Dict[str, Any],
    user_id: str,
    db,
    language: str
) -> Dict[str, Any]:
    """Check if a specific product is available in stock."""
    products = await db.search_products(arguments["product_name"])
    if products:
        product = products[0]
        product_details = await db.get_product_by_id(product.id)
        fulfillment_hours = getattr(product_details, 'fulfillment_time_hours', 48) if product_details else 48
        requires_prepayment = getattr(product_details, 'requires_prepayment', False) if product_details else False
        product_status = getattr(product_details, 'status', 'active') if product_details else 'active'
        
        is_discontinued = product_status == 'discontinued'
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


async def handle_get_product_details(
    arguments: Dict[str, Any],
    user_id: str,
    db,
    language: str
) -> Dict[str, Any]:
    """Get detailed information about a specific product."""
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


async def handle_search_products(
    arguments: Dict[str, Any],
    user_id: str,
    db,
    language: str
) -> Dict[str, Any]:
    """Search for products using semantic search."""
    query = arguments.get("query", "")
    category = arguments.get("category", "all")
    
    try:
        from core.rag import ProductSearch, VECS_AVAILABLE
        if not VECS_AVAILABLE or ProductSearch is None:
            raise ImportError("RAG not available")
        
        product_search = ProductSearch()
        
        filters = {"status": {"$eq": "active"}}
        if category != "all":
            category_map = {
                "chatgpt": "shared", "claude": "shared", "midjourney": "shared",
                "image": "shared", "code": "key", "writing": "shared"
            }
            if category in category_map:
                filters["type"] = {"$eq": category_map[category]}
        
        rag_results = await product_search.search(query, limit=5, filters=filters)
        
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
        
        # Fallback to text search if RAG didn't find enough
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
        
        return {"count": len(products), "products": products[:5]}
        
    except Exception as e:
        print(f"RAG search failed, using text search: {e}")
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


async def handle_get_catalog(
    arguments: Dict[str, Any],
    user_id: str,
    db,
    language: str
) -> Dict[str, Any]:
    """Get the full product catalog."""
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


async def handle_compare_products(
    arguments: Dict[str, Any],
    user_id: str,
    db,
    language: str
) -> Dict[str, Any]:
    """Compare two or more products."""
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


async def handle_create_purchase_intent(
    arguments: Dict[str, Any],
    user_id: str,
    db,
    language: str
) -> Dict[str, Any]:
    """Create a purchase intent when user wants to buy."""
    product_id_or_name = arguments.get("product_id", "")
    resolved_id, error = await resolve_product_id(product_id_or_name, db)
    if error:
        return {"success": False, "reason": error}
    
    product = await db.get_product_by_id(resolved_id)
    if not product:
        return {"success": False, "reason": "Product not found"}
    
    product_status = getattr(product, 'status', 'active')
    is_discontinued = product_status == 'discontinued'
    
    if is_discontinued:
        return {
            "success": False,
            "reason": "Product is discontinued. Please use waitlist."
        }
    
    if product.stock_count > 0:
        return {
            "success": True,
            "product_id": product.id,
            "product_name": product.name,
            "price": product.price,
            "order_type": "instant",
            "action": "show_payment_button"
        }
    else:
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
            "message": f"Will be made in {fulfillment_days}-{fulfillment_days + 1} days. 100% prepayment."
        }


async def handle_add_to_waitlist(
    arguments: Dict[str, Any],
    user_id: str,
    db,
    language: str
) -> Dict[str, Any]:
    """Add user to waitlist for an out-of-stock product."""
    try:
        product_name = arguments.get("product_name", "").strip()
        if not product_name:
            return {"success": False, "reason": "Product name is required"}
        
        await db.add_to_waitlist(user_id, product_name)
        return {
            "success": True,
            "product_name": product_name,
            "message": f"Added to waitlist for {product_name}"
        }
    except Exception as e:
        error_str = str(e)
        if "already" in error_str.lower() or "duplicate" in error_str.lower() or "unique" in error_str.lower():
            return {
                "success": True,
                "product_name": product_name,
                "message": f"You are already on the waitlist for {product_name}"
            }
        return {"success": False, "reason": "Failed to add to waitlist."}


# Export handlers mapping
PRODUCT_HANDLERS = {
    "check_product_availability": handle_check_product_availability,
    "get_product_details": handle_get_product_details,
    "search_products": handle_search_products,
    "get_catalog": handle_get_catalog,
    "compare_products": handle_compare_products,
    "create_purchase_intent": handle_create_purchase_intent,
    "add_to_waitlist": handle_add_to_waitlist,
}

