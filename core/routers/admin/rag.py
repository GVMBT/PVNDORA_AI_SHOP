"""
Admin RAG Router

RAG (semantic search) indexing endpoint.
"""

import os

from fastapi import APIRouter, Header, HTTPException

router = APIRouter(tags=["admin-rag"])


@router.post("/index-products")
async def admin_index_products(authorization: str = Header(None)):
    """Index all products for RAG (semantic search)"""
    cron_secret = os.environ.get("CRON_SECRET", "")
    if authorization != f"Bearer {cron_secret}":
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        from core.rag import get_product_search

        search = get_product_search()

        if not search.is_available:
            return {"success": False, "error": "RAG not available"}

        indexed = await search.index_all_products()
        return {"success": True, "indexed_products": indexed}

    except Exception as e:
        return {"success": False, "error": str(e)}
