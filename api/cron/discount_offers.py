"""
Discount Offers Cron Job
Schedule: 0 12 * * * (12:00 UTC daily)

Tasks:
1. Send offers to loyal customers (3+ purchases)
2. Send offers to inactive users (7+ days)
"""
from datetime import datetime, timezone
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import os

# Verify cron secret
CRON_SECRET = os.environ.get("CRON_SECRET", "")

# ASGI app
app = FastAPI()


@app.get("/api/cron/discount_offers")
async def discount_offers_entrypoint(request: Request):
    """
    Vercel Cron entrypoint for discount offers.
    """
    auth_header = request.headers.get("Authorization", "")
    if CRON_SECRET and auth_header != f"Bearer {CRON_SECRET}":
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    from core.services.database import get_database
    from core.services.domains.offers import OffersService
    
    db = get_database()
    offers_service = OffersService(db.client)
    
    now = datetime.now(timezone.utc)
    results = {
        "timestamp": now.isoformat(),
        "offers": {}
    }
    
    try:
        offer_results = await offers_service.process_all_offers()
        results["offers"] = offer_results
        results["success"] = True
        
    except Exception as e:
        results["success"] = False
        results["error"] = str(e)
    
    return JSONResponse(results)
