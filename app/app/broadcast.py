"""
Server Sent Events (SSE) broadcaster
The server can manage global Svelte UI state changes to all connected clients.
"""

from typing import Set
from asyncio import Queue
import logging

logger = logging.getLogger(__name__)

subscribers: Set[Queue] = set()


async def subscribe() -> Queue:
    q = Queue()
    subscribers.add(q)
    return q


def unsubscribe(q: Queue):
    subscribers.discard(q)


async def broadcast(event: dict):
    logger.info("Broadcasting event: {event}")
    for q in subscribers:
        await q.put(event)
