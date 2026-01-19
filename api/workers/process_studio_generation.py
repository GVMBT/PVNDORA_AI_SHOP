"""Studio Generation Worker.

Processes AI generation jobs via QStash.
Handles:
- Polling provider status
- Downloading results to Supabase Storage
- Updating generation record
- Sending realtime events
"""

import os
import sys
from pathlib import Path
from typing import Any

# Add project root to path for imports
_base_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_base_path))

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from core.logging import get_logger

logger = get_logger(__name__)

app = FastAPI()


class ProcessGenerationRequest(BaseModel):
    """Request payload for processing a generation."""
    generation_id: str
    model_id: str
    external_job_id: str
    user_id: str
    attempt: int = 1


async def _verify_qstash_signature(request: Request) -> bool:
    """Verify QStash webhook signature."""
    from upstash_qstash import Receiver

    qstash_current_signing_key = os.environ.get("QSTASH_CURRENT_SIGNING_KEY", "")
    qstash_next_signing_key = os.environ.get("QSTASH_NEXT_SIGNING_KEY", "")

    if not qstash_current_signing_key:
        logger.warning("QSTASH_CURRENT_SIGNING_KEY not set, skipping verification")
        return True

    try:
        receiver = Receiver(
            current_signing_key=qstash_current_signing_key,
            next_signing_key=qstash_next_signing_key,
        )

        body = await request.body()
        signature = request.headers.get("Upstash-Signature", "")

        receiver.verify(
            body=body.decode(),
            signature=signature,
            url=str(request.url),
        )
        return True
    except Exception:
        logger.exception("QStash signature verification failed")
        return False


async def _download_to_storage(
    source_url: str,
    user_id: str,
    generation_id: str,
    file_type: str,
    db: Any,
) -> str:
    """Download file from provider and upload to Supabase Storage.

    Args:
        source_url: URL to download from
        user_id: User ID for storage path
        generation_id: Generation ID for storage path
        file_type: 'video', 'audio', or 'image'
        db: Database instance

    Returns:
        Public URL in Supabase Storage
    """
    import httpx

    # Determine file extension
    ext_map = {
        "video": "mp4",
        "audio": "mp3",
        "image": "png",
    }
    ext = ext_map.get(file_type, "bin")

    # Download file
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.get(source_url)
        response.raise_for_status()
        content = response.content

    # Upload to Supabase Storage
    storage_path = f"{user_id}/{generation_id}/result.{ext}"

    await db.storage.from_("studio-results").upload(
        storage_path,
        content,
        {"content-type": f"{file_type}/{ext}"},
    )

    # Get public URL
    public_url = db.storage.from_("studio-results").get_public_url(storage_path)

    logger.info(f"Uploaded generation result to {storage_path}")
    return public_url


async def _create_thumbnail(
    result_url: str,
    user_id: str,
    generation_id: str,
    file_type: str,
    db: Any,
) -> str | None:
    """Create and upload thumbnail.

    For video: Extract first frame
    For image: Resize
    For audio: Generate waveform (optional)

    Returns:
        Thumbnail URL or None
    """
    # TODO: Implement thumbnail generation
    # For MVP, we'll skip this and let frontend handle preview
    return None


async def _emit_generation_event(
    user_id: str,
    generation_id: str,
    status: str,
    progress: int,
    result_url: str | None = None,
    error: str | None = None,
) -> None:
    """Emit realtime event for generation status update."""
    try:
        from core.db import get_redis
        import json

        redis = get_redis()
        stream_key = f"stream:realtime:studio:{user_id}"

        payload = {
            "type": "generation.status",
            "generation_id": generation_id,
            "status": status,
            "progress": progress,
            "result_url": result_url,
            "error": error,
            "timestamp": __import__("datetime").datetime.now(__import__("datetime").UTC).isoformat(),
        }

        await redis.xadd(stream_key, "*", {"data": json.dumps(payload)})
        logger.debug(f"Emitted generation event: {status} for {generation_id}")

    except Exception as e:
        logger.warning(f"Failed to emit generation event: {e}")


async def _process_generation(payload: ProcessGenerationRequest) -> dict[str, Any]:
    """Process a single generation job.

    This function:
    1. Checks generation status with provider
    2. If complete, downloads result to storage
    3. Updates generation record
    4. Emits realtime event
    5. Schedules retry if still processing
    """
    from core.services.database import get_database_async
    from core.studio.dispatcher import check_status
    from core.studio.adapters.base import GenerationStatus

    db = await get_database_async()

    # Check status with provider
    try:
        result = await check_status(payload.model_id, payload.external_job_id)
    except Exception as e:
        logger.exception(f"Failed to check status for {payload.generation_id}")

        # If too many attempts, mark as failed
        if payload.attempt >= 60:  # ~5 minutes with 5s intervals
            await _update_generation_failed(
                db, payload.generation_id, payload.user_id,
                f"Status check failed after {payload.attempt} attempts: {e}"
            )
            return {"status": "failed", "error": str(e)}

        # Schedule retry
        await _schedule_retry(payload, delay_seconds=5)
        return {"status": "retrying", "attempt": payload.attempt}

    # Emit progress event
    await _emit_generation_event(
        payload.user_id,
        payload.generation_id,
        result.status.value,
        result.progress,
    )

    if result.status == GenerationStatus.COMPLETED:
        # Download result to storage
        storage_url = None
        thumbnail_url = None

        if result.result_url:
            try:
                # Get generation type
                gen_result = await db.client.table("studio_generations") \
                    .select("type") \
                    .eq("id", payload.generation_id) \
                    .single() \
                    .execute()

                file_type = gen_result.data.get("type", "video") if gen_result.data else "video"

                storage_url = await _download_to_storage(
                    result.result_url,
                    payload.user_id,
                    payload.generation_id,
                    file_type,
                    db,
                )

                thumbnail_url = await _create_thumbnail(
                    storage_url,
                    payload.user_id,
                    payload.generation_id,
                    file_type,
                    db,
                )
            except Exception:
                logger.exception("Failed to download result")
                storage_url = result.result_url  # Use provider URL as fallback

        # Update generation record
        await db.client.table("studio_generations").update({
            "status": "completed",
            "progress": 100,
            "result_url": storage_url,
            "thumbnail_url": thumbnail_url,
            "duration_seconds": result.duration_seconds,
            "has_audio": result.has_audio,
        }).eq("id", payload.generation_id).execute()

        # Emit completion event
        await _emit_generation_event(
            payload.user_id,
            payload.generation_id,
            "completed",
            100,
            result_url=storage_url,
        )

        logger.info(f"Generation {payload.generation_id} completed")
        return {"status": "completed", "result_url": storage_url}

    if result.status == GenerationStatus.FAILED:
        await _update_generation_failed(
            db, payload.generation_id, payload.user_id,
            result.error_message or "Generation failed"
        )
        return {"status": "failed", "error": result.error_message}

    # Still processing - schedule retry
    if payload.attempt >= 120:  # ~10 minutes max
        await _update_generation_failed(
            db, payload.generation_id, payload.user_id,
            "Generation timed out"
        )
        return {"status": "failed", "error": "Timeout"}

    # Update progress
    await db.client.table("studio_generations").update({
        "progress": result.progress,
    }).eq("id", payload.generation_id).execute()

    await _schedule_retry(payload, delay_seconds=5)
    return {"status": "processing", "progress": result.progress}


async def _update_generation_failed(
    db: Any,
    generation_id: str,
    user_id: str,
    error_message: str,
) -> None:
    """Mark generation as failed and refund."""
    from core.studio.service import get_studio_service

    service = get_studio_service(db)
    await service.update_generation_status(
        generation_id,
        "failed",
        error_message=error_message,
    )

    await _emit_generation_event(
        user_id,
        generation_id,
        "failed",
        0,
        error=error_message,
    )


async def _schedule_retry(payload: ProcessGenerationRequest, delay_seconds: int = 5) -> None:
    """Schedule retry via QStash."""
    from upstash_qstash import Client

    qstash_token = os.environ.get("QSTASH_TOKEN", "")
    base_url = os.environ.get("BASE_URL", "")

    if not qstash_token or not base_url:
        logger.warning("QStash not configured, cannot schedule retry")
        return

    try:
        client = Client(qstash_token)

        await client.publish_json(
            url=f"{base_url}/api/workers/process_studio_generation",
            body={
                "generation_id": payload.generation_id,
                "model_id": payload.model_id,
                "external_job_id": payload.external_job_id,
                "user_id": payload.user_id,
                "attempt": payload.attempt + 1,
            },
            delay=f"{delay_seconds}s",
        )

        logger.debug(f"Scheduled retry #{payload.attempt + 1} for {payload.generation_id}")

    except Exception:
        logger.exception("Failed to schedule retry")


@app.post("/api/workers/process_studio_generation")
async def process_studio_generation(request: Request) -> JSONResponse:
    """QStash worker endpoint for processing studio generations."""
    # Verify QStash signature
    if not await _verify_qstash_signature(request):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse payload
    try:
        body = await request.json()
        payload = ProcessGenerationRequest(**body)
    except Exception as e:
        logger.exception("Invalid payload")
        raise HTTPException(status_code=400, detail=f"Invalid payload: {e}")

    logger.info(f"Processing generation {payload.generation_id}, attempt {payload.attempt}")

    # Process generation
    result = await _process_generation(payload)

    return JSONResponse(result)
