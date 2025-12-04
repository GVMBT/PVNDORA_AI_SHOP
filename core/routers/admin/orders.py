"""
Admin Orders & FAQ Router

Order and FAQ management endpoints.
"""
import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends

from src.services.database import get_database
from core.auth import verify_admin
from .models import CreateFAQRequest

router = APIRouter(tags=["admin-orders"])


# ==================== ORDERS ====================

@router.get("/orders")
async def admin_get_orders(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    admin=Depends(verify_admin)
):
    """Get all orders with optional filtering"""
    db = get_database()
    
    def execute_query():
        query = db.client.table("orders").select(
            "*, users(telegram_id, username, first_name), products(name)"
        ).order("created_at", desc=True).range(offset, offset + limit - 1)
        
        if status:
            query = query.eq("status", status)
        
        return query.execute()
    
    result = await asyncio.to_thread(execute_query)
    return {"orders": result.data if result.data else []}


# ==================== FAQ ====================

@router.post("/faq")
async def admin_create_faq(request: CreateFAQRequest, admin=Depends(verify_admin)):
    """Create a FAQ entry"""
    db = get_database()
    
    result = await asyncio.to_thread(
        lambda: db.client.table("faq").insert({
            "question": request.question,
            "answer": request.answer,
            "language_code": request.language_code,
            "category": request.category,
            "is_active": True
        }).execute()
    )
    
    if result.data:
        return {"success": True, "faq": result.data[0]}
    raise HTTPException(status_code=500, detail="Failed to create FAQ")


@router.get("/faq")
async def admin_get_faq(admin=Depends(verify_admin)):
    """Get all FAQ entries for admin"""
    db = get_database()
    
    result = await asyncio.to_thread(
        lambda: db.client.table("faq").select("*").order("language_code").order("category").execute()
    )
    
    return {"faq": result.data}
