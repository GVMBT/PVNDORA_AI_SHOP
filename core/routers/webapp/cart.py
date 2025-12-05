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
    """Get user's shopping cart with currency conversion."""
    from core.cart import get_cart_manager
    
    try:
        cart_manager = get_cart_manager()
        cart = await cart_manager.get_cart(user.id)
        
        db = get_database()
        db_user = await db.get_user_by_telegram_id(user.id)
        
        # Get currency service and convert prices
        currency = "USD"
        currency_service = None
        
        try:
            from core.db import get_redis
            from src.services.currency import get_currency_service
            redis = get_redis()  # get_redis() is synchronous, no await needed
            currency_service = get_currency_service(redis)
            currency = currency_service.get_user_currency(db_user.language_code if db_user else user.language_code)
        except Exception as e:
            print(f"Warning: Currency service unavailable: {e}, using USD")
        
        if not cart:
            return {
                "cart": None, "items": [], "total": 0.0, "subtotal": 0.0,
                "instant_total": 0.0, "prepaid_total": 0.0, 
                "promo_code": None, "promo_discount_percent": 0.0,
                "currency": currency
            }
        
        items_with_details = []
        total_converted = cart.total
        subtotal_converted = cart.subtotal
        instant_total_converted = cart.instant_total
        prepaid_total_converted = cart.prepaid_total
        
        for item in cart.items:
            product = await db.get_product_by_id(item.product_id)
            
            # Convert prices from USD to user currency
            unit_price_converted = float(item.unit_price)
            final_price_converted = float(item.final_price)
            total_price_converted = float(item.total_price)
            
            if currency_service and currency != "USD":
                try:
                    unit_price_converted = await currency_service.convert_price(float(item.unit_price), currency, round_to_int=True)
                    final_price_converted = await currency_service.convert_price(float(item.final_price), currency, round_to_int=True)
                    total_price_converted = await currency_service.convert_price(float(item.total_price), currency, round_to_int=True)
                except Exception as e:
                    print(f"Warning: Failed to convert cart item prices: {e}")
            
            items_with_details.append({
                "product_id": item.product_id, 
                "product_name": product.name if product else "Unknown",
                "quantity": item.quantity, 
                "instant_quantity": item.instant_quantity,
                "prepaid_quantity": item.prepaid_quantity, 
                "unit_price": unit_price_converted,
                "final_price": final_price_converted, 
                "total_price": total_price_converted, 
                "discount_percent": item.discount_percent,
                "currency": currency
            })
        
        # Convert totals
        if currency_service and currency != "USD":
            try:
                total_converted = await currency_service.convert_price(float(cart.total), currency, round_to_int=True)
                subtotal_converted = await currency_service.convert_price(float(cart.subtotal), currency, round_to_int=True)
                instant_total_converted = await currency_service.convert_price(float(cart.instant_total), currency, round_to_int=True)
                prepaid_total_converted = await currency_service.convert_price(float(cart.prepaid_total), currency, round_to_int=True)
            except Exception as e:
                print(f"Warning: Failed to convert cart totals: {e}")
        
        return {
            "cart": {
                "user_telegram_id": cart.user_telegram_id, 
                "created_at": cart.created_at, 
                "updated_at": cart.updated_at
            },
            "items": items_with_details, 
            "total": total_converted, 
            "subtotal": subtotal_converted,
            "instant_total": instant_total_converted, 
            "prepaid_total": prepaid_total_converted,
            "promo_code": cart.promo_code, 
            "promo_discount_percent": cart.promo_discount_percent,
            "currency": currency
        }
    except Exception as e:
        print(f"ERROR: Failed to get cart: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve cart: {str(e)}")
