"""
Cron Job: Update Exchange Rates
Schedule: 0 */6 * * * (every 6 hours)

NOTE: This cron is no longer used for currency conversion as all amounts are now in RUB.
It only updates USDT/RUB rate for withdrawals.
"""

import os
import sys
from datetime import UTC, datetime
from pathlib import Path

# Add project root to path
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

# ASGI app
app = FastAPI()


@app.get("/api/cron/update_exchange_rates")
@app.post("/api/cron/update_exchange_rates")
async def update_exchange_rates_entrypoint(request: Request):
    """
    Update USDT/RUB rate for withdrawal calculations.
    
    All other currency rates are no longer needed as system is RUB-only.
    """
    auth_header = request.headers.get("Authorization", "")
    if CRON_SECRET and auth_header != f"Bearer {CRON_SECRET}":
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    try:
        # Fetch USDT/RUB rate from a crypto exchange API
        usdt_rub_rate = await fetch_usdt_rub_rate()
        
        # Store in Redis for withdrawal calculations
        redis_url = os.environ.get("UPSTASH_REDIS_REST_URL", "")
        redis_token = os.environ.get("UPSTASH_REDIS_REST_TOKEN", "")
        
        if redis_url and redis_token:
            from upstash_redis.asyncio import Redis as AsyncRedis
            redis = AsyncRedis(url=redis_url, token=redis_token)
            await redis.setex("currency:rate:USDT_RUB", 3600, str(usdt_rub_rate))
            logger.info(f"Updated USDT/RUB rate in Redis: {usdt_rub_rate}")
        
        now = datetime.now(UTC).isoformat()
        result = {
            "success": True,
            "usdt_rub_rate": usdt_rub_rate,
            "timestamp": now,
            "note": "System is RUB-only. Only USDT rate needed for withdrawals.",
        }

        logger.info(f"Exchange rates updated: USDT/RUB = {usdt_rub_rate}")
        return JSONResponse(result)

    except Exception as e:
        logger.error(f"Failed to update exchange rates: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)


async def fetch_usdt_rub_rate() -> float:
    """
    Fetch current USDT/RUB rate from exchange API.
    
    Tries multiple sources for reliability.
    """
    # Try Binance P2P API (most accurate for RUB)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Binance P2P average rate
            response = await client.post(
                "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search",
                json={
                    "asset": "USDT",
                    "fiat": "RUB",
                    "merchantCheck": True,
                    "page": 1,
                    "rows": 10,
                    "tradeType": "BUY",
                },
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("data"):
                prices = [float(ad["adv"]["price"]) for ad in data["data"][:5]]
                if prices:
                    avg_rate = sum(prices) / len(prices)
                    logger.info(f"Got USDT/RUB from Binance P2P: {avg_rate}")
                    return avg_rate
    except Exception as e:
        logger.warning(f"Binance P2P failed: {e}")

    # Fallback: Try exchangerate-api (less accurate for crypto)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("https://api.exchangerate-api.com/v4/latest/USD")
            response.raise_for_status()
            data = response.json()
            rub_rate = data.get("rates", {}).get("RUB", 100.0)
            # USDT ≈ USD, so USDT/RUB ≈ USD/RUB
            logger.info(f"Got USDT/RUB from exchangerate-api: {rub_rate}")
            return rub_rate
    except Exception as e:
        logger.warning(f"exchangerate-api failed: {e}")

    # Last resort fallback
    logger.warning("Using fallback USDT/RUB rate: 100.0")
    return 100.0
