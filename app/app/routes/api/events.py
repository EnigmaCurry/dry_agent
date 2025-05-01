"""
Broadcast server events to all connected clients
"""

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from app.broadcast import subscribe, unsubscribe
import json
import logging

router = APIRouter()

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("/")
async def sse(request: Request):
    queue = await subscribe()

    async def event_stream():
        try:
            while True:
                # disconnect detection
                if await request.is_disconnected():
                    break

                event = await queue.get()
                yield f"event: {event['type']}\ndata: {json.dumps(event['data'])}\n\n"
        finally:
            unsubscribe(queue)

    return StreamingResponse(event_stream(), media_type="text/event-stream")
