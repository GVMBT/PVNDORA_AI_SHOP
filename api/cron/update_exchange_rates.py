"""
Cron Job: Update Exchange Rates
Schedule: Every hour (0 * * * *)

Fetches latest exchange rates from exchangerate-api.com and stores in Supabase.
This ensures runtime has always-available, up-to-date rates without external API dependency.
"""

import os
import httpx
from datetime import datetime, timezone

from supabase import create_client


# Supported currencies
SUPPORTED_CURRENCIES = [
    "USD", "RUB", "EUR", "UAH", "TRY", "INR", 
    "AED", "GBP", "CNY", "JPY", "KRW", "BRL"
]


async def update_rates():
    """Fetch rates from API and update Supabase."""
    
    # Initialize Supabase
    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    
    if not supabase_url or not supabase_key:
        return {"error": "Supabase not configured"}
    
    supabase = create_client(supabase_url, supabase_key)
    
    # Fetch rates from free API
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.exchangerate-api.com/v4/latest/USD"
            )
            response.raise_for_status()
            data = response.json()
            
        rates = data.get("rates", {})
        if not rates:
            return {"error": "No rates in API response"}
        
    except Exception as e:
        return {"error": f"API fetch failed: {e}"}
    
    # Update each supported currency
    updated = []
    now = datetime.now(timezone.utc).isoformat()
    
    for currency in SUPPORTED_CURRENCIES:
        rate = rates.get(currency)
        if rate:
            try:
                supabase.table("exchange_rates").upsert({
                    "currency": currency,
                    "rate": float(rate),
                    "updated_at": now
                }).execute()
                updated.append(currency)
            except Exception as e:
                print(f"Failed to update {currency}: {e}")
    
    return {
        "success": True,
        "updated": updated,
        "timestamp": now
    }


# Vercel serverless handler
async def handler(request):
    """Vercel cron handler."""
    from starlette.responses import JSONResponse
    
    # Verify cron secret (optional but recommended)
    auth_header = request.headers.get("Authorization", "")
    cron_secret = os.environ.get("CRON_SECRET", "")
    
    if cron_secret and auth_header != f"Bearer {cron_secret}":
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    result = await update_rates()
    
    if "error" in result:
        return JSONResponse(result, status_code=500)
    
    return JSONResponse(result)


# FastAPI router for local testing
def get_router():
    from fastapi import APIRouter
    router = APIRouter()
    
    @router.get("/api/cron/update_exchange_rates")
    @router.post("/api/cron/update_exchange_rates")
    async def cron_update_rates():
        return await update_rates()
    
    return router

