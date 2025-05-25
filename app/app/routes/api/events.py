"""
Broadcast server events to all connected clients
"""

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from app.broadcast import subscribe, unsubscribe
import logging
from .docker_context import get_docker_context, get_docker_context_names
from app.models.events import Event, ContextChangedEvent, ContextListEvent

router = APIRouter()

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("/")
async def sse(request: Request):
    queue = await subscribe()

    # Send initial events upon connection:
    # - current docker context
    # - list of docker contexts
    await queue.put(
        ContextChangedEvent(
            new_context=get_docker_context(),
        )
    )
    await queue.put(
        ContextListEvent(
            contexts=get_docker_context_names(),
        )
    )

    async def event_stream():
        try:
            while True:
                # disconnect detection
                if await request.is_disconnected():
                    break

                event: Event = await queue.get()
                yield f"event: {event.type}\ndata: {event.model_dump_json()}\n\n"
        finally:
            unsubscribe(queue)

    return StreamingResponse(event_stream(), media_type="text/event-stream")
