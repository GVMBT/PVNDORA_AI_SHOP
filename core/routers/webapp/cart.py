"""
WebApp Cart Router

Shopping cart endpoints.
"""
from fastapi import APIRouter, HTTPException, Depends

from src.services.database import get_database
from core.auth import verify_telegram_auth

router = APIRouter(tags=["webapp-cart"])


@router.get("/cart")
async def get_webapp_cart(user=Depends(verify_telegram_auth)):
    """Get user's shopping cart."""
    from core.cart import get_cart_manager
    
    try:
        cart_manager = get_cart_manager()
        cart = await cart_manager.get_cart(user.id)
        
        if not cart:
            return {
                "cart": None, "items": [], "total": 0.0, "subtotal": 0.0,
                "instant_total": 0.0, "prepaid_total": 0.0, 
                "promo_code": None, "promo_discount_percent": 0.0
            }
        
        db = get_database()
        items_with_details = []
        for item in cart.items:
            product = await db.get_product_by_id(item.product_id)
            items_with_details.append({
                "product_id": item.product_id, 
                "product_name": product.name if product else "Unknown",
                "quantity": item.quantity, 
                "instant_quantity": item.instant_quantity,
                "prepaid_quantity": item.prepaid_quantity, 
                "unit_price": item.unit_price,
                "final_price": item.final_price, 
                "total_price": item.total_price, 
                "discount_percent": item.discount_percent
            })
        
        return {
            "cart": {
                "user_telegram_id": cart.user_telegram_id, 
                "created_at": cart.created_at, 
                "updated_at": cart.updated_at
            },
            "items": items_with_details, 
            "total": cart.total, 
            "subtotal": cart.subtotal,
            "instant_total": cart.instant_total, 
            "prepaid_total": cart.prepaid_total,
            "promo_code": cart.promo_code, 
            "promo_discount_percent": cart.promo_discount_percent
        }
    except Exception as e:
        print(f"ERROR: Failed to get cart: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve cart: {str(e)}")
