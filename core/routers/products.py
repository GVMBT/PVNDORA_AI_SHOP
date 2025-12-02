"""
Products API Router

Public endpoints for product catalog.
Merged /api/products and /api/webapp/products to avoid duplication.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from src.services.database import get_database
from src.utils.validators import validate_telegram_init_data, extract_user_from_init_data

router = APIRouter(tags=["products"])


# ==================== PYDANTIC MODELS ====================

class ProductResponse(BaseModel):
    id: str
    name: str
    description: str
    price: float
    type: str
    status: str
    stock_count: int
    warranty_hours: int
    rating: float = 0
    reviews_count: int = 0


# ==================== PUBLIC PRODUCTS API ====================

@router.get("/api/products")
async def get_products():
    """Get all available products (public)"""
    db = get_database()
    products = await db.get_products(status="active")
    
    result = []
    for p in products:
        rating_info = await db.get_product_rating(p.id)
        result.append(ProductResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            price=p.price,
            type=p.type,
            status=p.status,
            stock_count=p.stock_count,
            warranty_hours=p.warranty_hours,
            rating=rating_info["average"],
            reviews_count=rating_info["count"]
        ))
    
    return result


@router.get("/api/products/{product_id}")
async def get_product(product_id: str):
    """Get product by ID (public)"""
    db = get_database()
    product = await db.get_product_by_id(product_id)
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    rating_info = await db.get_product_rating(product_id)
    reviews = await db.get_product_reviews(product_id, limit=5)
    
    return {
        "id": product.id,
        "name": product.name,
        "description": product.description,
        "price": product.price,
        "type": product.type,
        "status": product.status,
        "stock_count": product.stock_count,
        "warranty_hours": product.warranty_hours,
        "fulfillment_time_hours": product.fulfillment_time_hours,
        "rating": rating_info["average"],
        "reviews_count": rating_info["count"],
        "reviews": reviews
    }


# ==================== WEBAPP PRODUCTS API ====================

@router.get("/api/webapp/products/{product_id}")
async def get_webapp_product(
    product_id: str,
    authorization: Optional[str] = Header(None)
):
    """Get product details for webapp (with user-specific info)"""
    db = get_database()
    
    # Verify Telegram Mini App auth
    user_data = None
    if authorization and authorization.startswith("tma "):
        init_data = authorization[4:]
        if validate_telegram_init_data(init_data):
            user_data = extract_user_from_init_data(init_data)
    
    product = await db.get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    rating_info = await db.get_product_rating(product_id)
    reviews = await db.get_product_reviews(product_id, limit=5)
    
    # Check if user has product in wishlist
    in_wishlist = False
    if user_data:
        user = await db.get_user_by_telegram_id(user_data.get("id"))
        if user:
            wishlist = await db.get_wishlist(user.id)
            in_wishlist = any(p.id == product_id for p in wishlist)
    
    # Get stock status
    stock_result = db.client.table("stock_items").select(
        "id", count="exact"
    ).eq("product_id", product_id).eq("is_sold", False).execute()
    
    available_stock = getattr(stock_result, 'count', 0) or 0
    
    return {
        "id": product.id,
        "name": product.name,
        "description": product.description,
        "price": product.price,
        "type": product.type,
        "status": product.status,
        "stock_count": available_stock,
        "warranty_hours": product.warranty_hours,
        "fulfillment_time_hours": getattr(product, 'fulfillment_time_hours', 48),
        "instructions": getattr(product, 'instructions', ''),
        "msrp": getattr(product, 'msrp', None),
        "duration_days": getattr(product, 'duration_days', None),
        "rating": rating_info["average"],
        "reviews_count": rating_info["count"],
        "reviews": reviews,
        "in_wishlist": in_wishlist
    }


@router.get("/api/webapp/products")
async def get_webapp_products(
    authorization: Optional[str] = Header(None)
):
    """Get all products for webapp (with user-specific info)"""
    db = get_database()
    
    # Verify Telegram Mini App auth
    user_data = None
    if authorization and authorization.startswith("tma "):
        init_data = authorization[4:]
        if validate_telegram_init_data(init_data):
            user_data = extract_user_from_init_data(init_data)
    
    products = await db.get_products(status="active")
    
    # Get user wishlist if authenticated
    wishlist_ids = set()
    if user_data:
        user = await db.get_user_by_telegram_id(user_data.get("id"))
        if user:
            wishlist = await db.get_wishlist(user.id)
            wishlist_ids = {p.id for p in wishlist}
    
    result = []
    for p in products:
        rating_info = await db.get_product_rating(p.id)
        result.append({
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "price": p.price,
            "type": p.type,
            "status": p.status,
            "stock_count": p.stock_count,
            "warranty_hours": p.warranty_hours,
            "fulfillment_time_hours": getattr(p, 'fulfillment_time_hours', 48),
            "msrp": getattr(p, 'msrp', None),
            "duration_days": getattr(p, 'duration_days', None),
            "rating": rating_info["average"],
            "reviews_count": rating_info["count"],
            "in_wishlist": p.id in wishlist_ids
        })
    
    return result

