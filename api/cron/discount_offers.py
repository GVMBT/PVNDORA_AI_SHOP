"""Discount Offers Cron Job
Schedule: 0 12 * * * (12:00 UTC daily).

Tasks:
1. Send offers to loyal customers (3+ purchases)
2. Send offers to inactive users (7+ days)
"""

import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Add project root to path for imports BEFORE any core.* imports
_base_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_base_path))
if str(_base_path) not in sys.path:
    sys.path.insert(0, str(_base_path.resolve()))

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# Verify cron secret
CRON_SECRET = os.environ.get("CRON_SECRET", "")

# ASGI app
app = FastAPI()


@app.get("/api/cron/discount_offers")
async def discount_offers_entrypoint(request: Request) -> dict[str, str | int]:
    """Vercel Cron entrypoint for discount offers."""
    auth_header = request.headers.get("Authorization", "")
    if CRON_SECRET and auth_header != f"Bearer {CRON_SECRET}":
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    from core.services.database import get_database_async
    from core.services.domains.offers import OffersService

    db = await get_database_async()
    offers_service = OffersService(db.client)

    now = datetime.now(UTC)
    results: dict[str, Any] = {"timestamp": now.isoformat(), "offers": {}}

    try:
        offer_results = await offers_service.process_all_offers()
        results["offers"] = offer_results
        results["success"] = True

    except Exception as e:
        results["success"] = False
        results["error"] = str(e)

    return JSONResponse(results)
