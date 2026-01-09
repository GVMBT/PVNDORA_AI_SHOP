"""
Admin Promo Codes API

CRUD operations for promotional codes.
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from core.auth import verify_admin
from core.services.database import get_database
from core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["admin-promo"])


class PromoCodeCreate(BaseModel):
    code: str
    discount_percent: int
    expires_at: Optional[str] = None
    usage_limit: Optional[int] = None
    is_active: bool = True
    product_id: Optional[str] = None  # NULL = cart-wide, NOT NULL = product-specific


class PromoCodeUpdate(BaseModel):
    code: Optional[str] = None
    discount_percent: Optional[int] = None
    expires_at: Optional[str] = None
    usage_limit: Optional[int] = None
    is_active: Optional[bool] = None
    product_id: Optional[str] = None  # NULL = cart-wide, NOT NULL = product-specific


class PromoCodeResponse(BaseModel):
    id: str
    code: str
    discount_percent: int
    expires_at: Optional[str]
    usage_limit: Optional[int]
    usage_count: int
    is_active: bool
    product_id: Optional[str] = None  # NULL = cart-wide, NOT NULL = product-specific
    created_at: str


@router.get("/promo")
async def list_promo_codes(admin=Depends(verify_admin)) -> List[dict]:
    """Get all promo codes."""
    db = get_database()
    
    try:
        result = db.client.table("promo_codes").select("*").order("created_at", desc=True).execute()
        
        return [
            {
                "id": p["id"],
                "code": p["code"],
                "discount_percent": p["discount_percent"],
                "expires_at": p.get("expires_at"),
                "usage_limit": p.get("usage_limit"),
                "usage_count": p.get("usage_count", 0),
                "is_active": p.get("is_active", True),
                "product_id": p.get("product_id"),  # NULL = cart-wide, NOT NULL = product-specific
                "created_at": p.get("created_at"),
            }
            for p in (result.data or [])
        ]
    except Exception as e:
        logger.error(f"Failed to list promo codes: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch promo codes")


@router.post("/promo")
async def create_promo_code(request: PromoCodeCreate, admin=Depends(verify_admin)) -> dict:
    """Create a new promo code."""
    db = get_database()
    
    # Check if code already exists
    existing = db.client.table("promo_codes").select("id").eq("code", request.code.upper()).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Promo code already exists")
    
    try:
        # Validate product_id if provided
        if request.product_id:
            product_check = db.client.table("products").select("id").eq("id", request.product_id).execute()
            if not product_check.data:
                raise HTTPException(status_code=400, detail=f"Product {request.product_id} not found")
        
        data = {
            "code": request.code.upper(),
            "discount_percent": request.discount_percent,
            "is_active": request.is_active,
            "usage_count": 0,
        }
        
        if request.expires_at:
            data["expires_at"] = request.expires_at
        if request.usage_limit:
            data["usage_limit"] = request.usage_limit
        if request.product_id:
            data["product_id"] = request.product_id  # NULL = cart-wide, NOT NULL = product-specific
        
        result = db.client.table("promo_codes").insert(data).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create promo code")
        
        p = result.data[0]
        return {
            "id": p["id"],
            "code": p["code"],
            "discount_percent": p["discount_percent"],
            "expires_at": p.get("expires_at"),
            "usage_limit": p.get("usage_limit"),
            "usage_count": 0,
            "is_active": p.get("is_active", True),
            "product_id": p.get("product_id"),  # NULL = cart-wide, NOT NULL = product-specific
            "created_at": p.get("created_at"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create promo code: {e}")
        raise HTTPException(status_code=500, detail="Failed to create promo code")


@router.put("/promo/{promo_id}")
async def update_promo_code(promo_id: str, request: PromoCodeUpdate, admin=Depends(verify_admin)) -> dict:
    """Update an existing promo code."""
    db = get_database()
    
    try:
        # Validate product_id if provided
        if request.product_id is not None:
            if request.product_id:
                product_check = db.client.table("products").select("id").eq("id", request.product_id).execute()
                if not product_check.data:
                    raise HTTPException(status_code=400, detail=f"Product {request.product_id} not found")
        
        update_data = {}
        
        if request.code is not None:
            update_data["code"] = request.code.upper()
        if request.discount_percent is not None:
            update_data["discount_percent"] = request.discount_percent
        if request.expires_at is not None:
            update_data["expires_at"] = request.expires_at
        if request.usage_limit is not None:
            update_data["usage_limit"] = request.usage_limit
        if request.is_active is not None:
            update_data["is_active"] = request.is_active
        if request.product_id is not None:
            update_data["product_id"] = request.product_id  # NULL = cart-wide, NOT NULL = product-specific
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        result = db.client.table("promo_codes").update(update_data).eq("id", promo_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Promo code not found")
        
        p = result.data[0]
        return {
            "id": p["id"],
            "code": p["code"],
            "discount_percent": p["discount_percent"],
            "expires_at": p.get("expires_at"),
            "usage_limit": p.get("usage_limit"),
            "usage_count": p.get("usage_count", 0),
            "is_active": p.get("is_active", True),
            "product_id": p.get("product_id"),  # NULL = cart-wide, NOT NULL = product-specific
            "created_at": p.get("created_at"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update promo code: {e}")
        raise HTTPException(status_code=500, detail="Failed to update promo code")


@router.delete("/promo/{promo_id}")
async def delete_promo_code(promo_id: str, admin=Depends(verify_admin)) -> dict:
    """Delete a promo code."""
    db = get_database()
    
    try:
        result = db.client.table("promo_codes").delete().eq("id", promo_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Promo code not found")
        
        return {"success": True, "message": "Promo code deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete promo code: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete promo code")
