from pathlib import Path
import os
import aiosql
from typing import AsyncGenerator, AsyncIterator, Optional, Callable
import aiosqlite

from app.models.chat_model import ChatModel

DB_PATH = Path(os.getenv("HOME")) / "dry_agent" / "database" / "dry_agent.db"

CHAT_QUERIES = aiosql.from_path(
    Path(__file__).parent.parent / "models/chat_model.sql",
    "aiosqlite",
)


def connection_provider() -> Callable[[], aiosqlite.Connection]:
    # Note: aiosqlite.Connection supports async context management
    return lambda: aiosqlite.connect(DB_PATH)


async def get_chat_model() -> AsyncGenerator[ChatModel, None]:
    """
    Yields a ChatModel backed by a fresh aiosqlite.Connection.
    """
    yield ChatModel(connection_provider(), CHAT_QUERIES)
