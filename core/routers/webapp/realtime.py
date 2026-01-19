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

# Polling interval for reading new stream entries (seconds)
# Note: upstash-redis REST API does NOT support blocking xread,
# so we use asyncio.sleep() for polling instead
POLL_INTERVAL_SECS = 1.0  # 1 second

# Maximum number of events to read per stream per poll
MAX_EVENTS_PER_POLL = 10

# Maximum number of events to send on initial connection (to avoid overwhelming client)
MAX_INITIAL_EVENTS = 20

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

    # Track if this is the first poll (initial connection)
    is_first_poll = True
    initial_events_sent = 0

    while True:
        try:
            # Read from all streams (non-blocking, upstash REST doesn't support block)
            # We read entries after last_ids for each stream
            has_events = False
            for stream_key in stream_keys:
                last_id = last_ids.get(stream_key, "$")

                # On first poll, read only recent events to avoid overwhelming client
                if is_first_poll and last_id == "$":
                    # Read all events (limited by MAX_INITIAL_EVENTS * 2 to get enough for last N)
                    # Then take only the last MAX_INITIAL_EVENTS to send newest events
                    try:
                        # Read more than needed to ensure we get the latest
                        all_entries = await redis.xrange(
                            stream_key, start="-", end="+", count=MAX_INITIAL_EVENTS * 2
                        )
                        if all_entries:
                            # Take only the last MAX_INITIAL_EVENTS (newest events)
                            entries = all_entries[-MAX_INITIAL_EVENTS:]
                            has_events = True
                            for entry_id, fields in entries:
                                last_ids[stream_key] = entry_id
                                data = fields.get("data", "{}")
                                if isinstance(data, str):
                                    try:
                                        parsed = json.loads(data)
                                        yield f"data: {json.dumps(parsed)}\n\n"
                                        initial_events_sent += 1
                                    except json.JSONDecodeError:
                                        logger.warning(f"Invalid JSON in stream {stream_key}: {data}")
                                else:
                                    yield f"data: {json.dumps(data)}\n\n"
                                    initial_events_sent += 1
                        else:
                            # No events, set to "0" to start reading new events
                            last_ids[stream_key] = "0"
                    except Exception as stream_err:
                        logger.warning(f"Error reading initial events from {stream_key}: {stream_err}")
                        last_ids[stream_key] = "0"
                    continue

                # For subsequent polls, read new events after last_id
                if last_id in {"$", "0"}:
                    # Skip if no last_id yet (will be set on next poll)
                    if last_id == "$":
                        last_ids[stream_key] = "0"
                    continue

                try:
                    # Read entries after last_id using xrange
                    # Format: XRANGE stream_key (last_id +inf COUNT MAX_EVENTS_PER_POLL
                    entries = await redis.xrange(
                        stream_key, start=f"({last_id}", end="+", count=MAX_EVENTS_PER_POLL
                    )
                    if entries:
                        has_events = True
                        for entry_id, fields in entries:
                            last_ids[stream_key] = entry_id
                            data = fields.get("data", "{}")
                            if isinstance(data, str):
                                try:
                                    parsed = json.loads(data)
                                    yield f"data: {json.dumps(parsed)}\n\n"
                                except json.JSONDecodeError:
                                    logger.warning(f"Invalid JSON in stream {stream_key}: {data}")
                            else:
                                yield f"data: {json.dumps(data)}\n\n"
                except Exception as stream_err:
                    logger.warning(f"Error reading stream {stream_key}: {stream_err}")

            # Mark first poll as complete
            if is_first_poll:
                is_first_poll = False
                if initial_events_sent > 0:
                    logger.debug(f"Sent {initial_events_sent} initial events on connection")

            # Send keep-alive if no new entries
            if not has_events:
                yield ": keep-alive\n\n"

            # Wait before next poll (non-blocking polling)
            await asyncio.sleep(POLL_INTERVAL_SECS)

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
        - user_id: User UUID (for user-specific streams) - optional, can be auto-detected from auth
        - channels: Comma-separated list of channels (profile, orders, admin, leaderboard)
    """
    # Get query parameters
    user_id = request.query_params.get("user_id")
    channels_param = request.query_params.get("channels", "profile,orders,leaderboard")

    # Auto-detect user_id from authentication if not provided in query
    if not user_id and user:
        try:
            from core.services.database import get_database_async

            # Get user_id from database using telegram_id
            db = await get_database_async()
            db_user = await db.get_user_by_telegram_id(user.id)
            if db_user:
                user_id = str(db_user.id)
                logger.debug(f"Auto-detected user_id from auth: {user_id}")
        except Exception as e:
            logger.debug(f"Could not auto-detect user_id from auth: {e}")

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
