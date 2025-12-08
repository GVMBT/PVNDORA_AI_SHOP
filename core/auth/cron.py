"""Cron secret validation."""
import os
from fastapi import Header, HTTPException


async def verify_cron_secret(
    authorization: str = Header(None, alias="Authorization")
):
    """
    Verify CRON_SECRET for scheduled jobs and internal workers.
    
    Use for cron endpoints and QStash workers.
    """
    cron_secret = os.environ.get("CRON_SECRET", "")
    
    if not cron_secret:
        raise HTTPException(status_code=500, detail="CRON_SECRET not configured")
    
    if authorization != f"Bearer {cron_secret}":
        raise HTTPException(status_code=401, detail="Invalid CRON_SECRET")
    
    return True

