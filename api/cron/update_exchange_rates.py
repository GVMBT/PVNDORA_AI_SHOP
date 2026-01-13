"""
Cron Job: Update Exchange Rates
Schedule: 0 */6 * * * (every 6 hours)

Fetches latest exchange rates from exchangerate-api.com and stores in Supabase.
This ensures runtime has always-available, up-to-date rates without external API dependency.
"""

import os
import sys
from datetime import UTC, datetime
from pathlib import Path

# Add project root to path for imports BEFORE any core.* imports
_base_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_base_path))
if str(_base_path) not in sys.path:
    sys.path.insert(0, str(_base_path.resolve()))

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from core.logging import get_logger

logger = get_logger(__name__)

CRON_SECRET = os.environ.get("CRON_SECRET", "")

# Supported currencies
SUPPORTED_CURRENCIES = [
    "USD",
    "RUB",
    "EUR",
    "UAH",
    "TRY",
    "INR",
    "AED",
    "GBP",
    "CNY",
    "JPY",
    "KRW",
    "BRL",
]

# ASGI app (only export app to Vercel, avoid 'handler' symbol)
app = FastAPI()


@app.get("/api/cron/update_exchange_rates")
@app.post("/api/cron/update_exchange_rates")
async def update_exchange_rates_entrypoint(request: Request):
    """
    Vercel Cron entrypoint for updating exchange rates.
    """
    auth_header = request.headers.get("Authorization", "")
    if CRON_SECRET and auth_header != f"Bearer {CRON_SECRET}":
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    from supabase._async.client import create_client as acreate_client

    # Initialize async Supabase client
    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

    if not supabase_url or not supabase_key:
        logger.error("Supabase not configured")
        return JSONResponse({"error": "Supabase not configured"}, status_code=500)

    try:
        supabase = await acreate_client(supabase_url, supabase_key)

        # Fetch rates from free API
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get("https://api.exchangerate-api.com/v4/latest/USD")
                response.raise_for_status()
                data = response.json()

            rates = data.get("rates", {})
            if not rates:
                logger.error("No rates in API response")
                return JSONResponse({"error": "No rates in API response"}, status_code=500)

        except Exception as e:
            logger.error(f"API fetch failed: {e}", exc_info=True)
            return JSONResponse({"error": f"API fetch failed: {e}"}, status_code=500)

        # Update each supported currency
        updated = []
        failed = []
        now = datetime.now(UTC).isoformat()

        for currency in SUPPORTED_CURRENCIES:
            rate = rates.get(currency)
            if rate:
                try:
                    await supabase.table("exchange_rates").upsert(
                        {"currency": currency, "rate": float(rate), "updated_at": now}
                    ).execute()
                    updated.append(currency)
                    logger.info(f"Updated {currency} rate: {rate}")
                except Exception as e:
                    logger.error(f"Failed to update {currency}: {e}", exc_info=True)
                    failed.append(currency)
            else:
                logger.warning(f"Rate not found for {currency}")
                failed.append(currency)

        result = {"success": True, "updated": updated, "failed": failed, "timestamp": now}

        if failed:
            logger.warning(f"Some currencies failed to update: {failed}")

        logger.info(
            f"Exchange rates updated: {len(updated)}/{len(SUPPORTED_CURRENCIES)} currencies"
        )
        return JSONResponse(result)

    except Exception as e:
        logger.error(f"Failed to update exchange rates: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)
