"""Realtime SSE Endpoint for Upstash Realtime.

Provides Server-Sent Events (SSE) endpoint for real-time updates.
Uses Redis Streams to read events and stream them to clients.
"""

import asyncio
import json
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from core.db import get_redis
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["realtime"])

# Polling interval for reading new stream entries (milliseconds)
POLL_INTERVAL_MS = 1000  # 1 second

# Redis Stream key prefixes (constants to avoid duplication)
STREAM_PREFIX_PROFILE = "stream:realtime:profile:"
STREAM_PREFIX_ORDERS = "stream:realtime:orders:"
STREAM_PREFIX_ADMIN_WITHDRAWALS = "stream:realtime:admin:withdrawals"
STREAM_PREFIX_ADMIN_ORDERS = "stream:realtime:admin:orders"
STREAM_PREFIX_ADMIN_ACCOUNTING = "stream:realtime:admin:accounting"
STREAM_PREFIX_LEADERBOARD = "stream:realtime:leaderboard"


def _build_streams_dict(stream_keys: list[str], last_ids: dict[str, str]) -> dict[str, str]:
    """Build streams dict for xread (reduces cognitive complexity)."""
    return {key: last_ids.get(key, "$") for key in stream_keys}


def _process_stream_results(
    results: list[tuple[str, list[tuple[str, dict[str, str]]]]],
    last_ids: dict[str, str],
) -> Any:
    """Process stream results and yield SSE events (reduces cognitive complexity)."""
    for stream_key, entries in results:
        for entry_id, fields in entries:
            # Update last_id for this stream
            last_ids[str(stream_key)] = entry_id

            # Extract and format data
            data = fields.get("data", "{}")
            if isinstance(data, str):
                try:
                    parsed = json.loads(data)
                    yield f"data: {json.dumps(parsed)}\n\n"
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in stream {stream_key}: {data}")
            else:
                yield f"data: {json.dumps(data)}\n\n"


async def _stream_events_generator(
    stream_keys: list[str], last_ids: dict[str, str] | None = None
) -> Any:
    """Generate SSE events from Redis Streams.

    Args:
        stream_keys: List of stream keys to read from
        last_ids: Dictionary mapping stream keys to last read entry IDs (for resume)
    """
    redis = get_redis()
    if last_ids is None:
        last_ids = dict.fromkeys(stream_keys, "$")  # Start from latest

    while True:
        try:
            streams_dict = _build_streams_dict(stream_keys, last_ids)
            results = await redis.xread(streams=streams_dict, count=1, block=POLL_INTERVAL_MS)

            for event in _process_stream_results(results, last_ids):
                yield event

            # Send keep-alive if no new entries
            if not results:
                yield ": keep-alive\n\n"

        except asyncio.CancelledError:
            logger.debug("Realtime stream cancelled")
            raise  # Re-raise to properly handle cancellation
        except Exception as e:
            logger.error(f"Error in realtime stream: {e}", exc_info=True)
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
            await asyncio.sleep(1)  # Wait before retrying


def _determine_stream_keys(channels_param: str, user_id: str | None) -> list[str]:
    """Determine stream keys based on channels parameter (reduces cognitive complexity).

    Args:
        channels_param: Comma-separated list of channels
        user_id: User UUID (optional)

    Returns:
        List of stream keys to subscribe to
    """
    stream_keys: list[str] = []

    if "profile" in channels_param and user_id:
        stream_keys.append(f"{STREAM_PREFIX_PROFILE}{user_id}")

    if "orders" in channels_param and user_id:
        stream_keys.append(f"{STREAM_PREFIX_ORDERS}{user_id}")

    if "admin" in channels_param:
        stream_keys.extend(
            [
                STREAM_PREFIX_ADMIN_WITHDRAWALS,
                STREAM_PREFIX_ADMIN_ORDERS,
                STREAM_PREFIX_ADMIN_ACCOUNTING,
            ]
        )

    if "leaderboard" in channels_param:
        stream_keys.append(STREAM_PREFIX_LEADERBOARD)

    if not stream_keys:
        # Default: all available streams for user
        if user_id:
            stream_keys.extend(
                [
                    f"{STREAM_PREFIX_PROFILE}{user_id}",
                    f"{STREAM_PREFIX_ORDERS}{user_id}",
                    STREAM_PREFIX_LEADERBOARD,
                ]
            )
        else:
            stream_keys = [STREAM_PREFIX_LEADERBOARD]

    return stream_keys


@router.get("/realtime")
async def realtime_stream(
    request: Request, user: Any = None  # Optional auth via verify_telegram_auth
) -> StreamingResponse:
    """SSE endpoint for real-time updates.

    Streams events from Redis Streams to clients via Server-Sent Events.
    Supports multiple stream subscriptions based on user_id.

    Query params:
        - user_id: User UUID (for user-specific streams)
        - channels: Comma-separated list of channels (profile, orders, admin, leaderboard)
    """
    # Get query parameters
    user_id = request.query_params.get("user_id")
    channels_param = request.query_params.get("channels", "profile,orders,leaderboard")

    # Determine stream keys based on channels
    stream_keys = _determine_stream_keys(channels_param, user_id)

    logger.debug(f"Realtime SSE connection: streams={stream_keys}")

    async def event_generator():
        async for event in _stream_events_generator(stream_keys):
            yield event
            # Check if client disconnected
            if await request.is_disconnected():
                logger.debug("Client disconnected from realtime stream")
                break

    headers = {
        "Cache-Control": "no-cache",
        "Content-Type": "text/event-stream",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",  # Disable nginx buffering
    }

    return StreamingResponse(event_generator(), headers=headers)
