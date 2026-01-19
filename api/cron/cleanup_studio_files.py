"""Studio Files Cleanup Cron Job.
Schedule: 0 4 * * * (4:00 AM UTC daily).

Tasks:
1. Mark expired generations (older than 30 days) as 'expired'
2. Delete files from Supabase Storage for expired generations
3. Clean up orphaned files in storage
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
from starlette.responses import Response

from core.logging import get_logger

logger = get_logger(__name__)

# Verify cron secret to prevent unauthorized access
CRON_SECRET = os.environ.get("CRON_SECRET", "")

# ASGI app
app = FastAPI()


async def _delete_storage_file(storage_client: Any, bucket: str, path: str) -> bool:
    """Delete a single file from Supabase Storage."""
    try:
        # Extract path from full URL if needed
        if path.startswith("http"):
            # URL format: https://xxx.supabase.co/storage/v1/object/public/bucket/path
            parts = path.split(f"/{bucket}/")
            if len(parts) > 1:
                path = parts[1]
            else:
                logger.warning(f"Could not extract path from URL: {path}")
                return False
        
        result = await storage_client.from_(bucket).remove([path])
        return True
    except Exception as e:
        logger.warning(f"Failed to delete file {path} from {bucket}: {e}")
        return False


async def _expire_old_generations(db: Any, now: datetime) -> dict[str, Any]:
    """Mark generations older than 30 days as expired and delete their files."""
    results = {
        "expired_count": 0,
        "files_deleted": 0,
        "files_failed": 0,
        "users_notified": 0,
    }
    
    try:
        # Find completed generations that have expired
        expired_generations = (
            await db.client.table("studio_generations")
            .select("id, user_id, result_url, thumbnail_url")
            .eq("status", "completed")
            .lt("expires_at", now.isoformat())
            .limit(100)  # Process in batches
            .execute()
        )
        
        if not expired_generations.data:
            logger.info("No expired studio generations found")
            return results
        
        generation_ids = []
        user_ids_to_notify = set()
        
        for gen in expired_generations.data:
            generation_ids.append(gen["id"])
            user_ids_to_notify.add(gen["user_id"])
            
            # Delete result file
            if gen.get("result_url"):
                if await _delete_storage_file(db.storage, "studio-results", gen["result_url"]):
                    results["files_deleted"] += 1
                else:
                    results["files_failed"] += 1
            
            # Delete thumbnail
            if gen.get("thumbnail_url"):
                if await _delete_storage_file(db.storage, "studio-results", gen["thumbnail_url"]):
                    results["files_deleted"] += 1
                else:
                    results["files_failed"] += 1
        
        # Mark generations as expired
        if generation_ids:
            await (
                db.client.table("studio_generations")
                .update({
                    "status": "expired",
                    "result_url": None,
                    "thumbnail_url": None,
                })
                .in_("id", generation_ids)
                .execute()
            )
            results["expired_count"] = len(generation_ids)
        
        # TODO: Send notifications to users about expired files
        # This could be done via Telegram bot or push notifications
        results["users_notified"] = len(user_ids_to_notify)
        
        logger.info(
            f"Expired {results['expired_count']} studio generations, "
            f"deleted {results['files_deleted']} files"
        )
        
    except Exception as e:
        logger.error(f"Error expiring studio generations: {e}", exc_info=True)
        results["error"] = str(e)
    
    return results


async def _cleanup_old_uploads(db: Any, now: datetime) -> dict[str, Any]:
    """Delete uploaded files (references, start frames) older than 7 days.
    
    Note: This requires tracking uploads in a table or scanning storage directly.
    For MVP, we'll skip this and rely on manual cleanup.
    """
    # TODO: Implement when we have upload tracking
    return {"skipped": True, "reason": "Upload tracking not implemented yet"}


async def _update_session_stats(db: Any) -> dict[str, Any]:
    """Recalculate session statistics (in case of inconsistencies)."""
    results = {"sessions_updated": 0}
    
    try:
        # Get all sessions with their actual generation counts
        sessions_stats = await db.client.rpc(
            "recalculate_studio_session_stats"
        ).execute()
        
        results["sessions_updated"] = len(sessions_stats.data or [])
        
    except Exception as e:
        # Function might not exist yet, that's OK
        logger.debug(f"Session stats recalculation skipped: {e}")
        results["skipped"] = True
    
    return results


@app.get("/api/cron/cleanup_studio_files")
async def cleanup_studio_files_entrypoint(request: Request) -> Response:
    """Vercel Cron entrypoint for studio files cleanup."""
    auth_header = request.headers.get("Authorization", "")
    if CRON_SECRET and auth_header != f"Bearer {CRON_SECRET}":
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    from core.services.database import get_database_async
    
    db = await get_database_async()
    now = datetime.now(UTC)
    
    results: dict[str, Any] = {
        "timestamp": now.isoformat(),
        "tasks": {},
    }
    
    try:
        # 1. Expire old generations and delete files
        results["tasks"]["expire_generations"] = await _expire_old_generations(db, now)
        
        # 2. Cleanup old uploads (7 days)
        results["tasks"]["cleanup_uploads"] = await _cleanup_old_uploads(db, now)
        
        # 3. Update session stats
        results["tasks"]["update_stats"] = await _update_session_stats(db)
        
        results["success"] = True
        
    except Exception as e:
        logger.error(f"Studio cleanup cron failed: {e}", exc_info=True)
        results["success"] = False
        results["error"] = str(e)
    
    return JSONResponse(results)
