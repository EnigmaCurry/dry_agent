from pathlib import Path
import os
import aiosql
from typing import AsyncGenerator, AsyncIterator, Optional
import aiosqlite

from app.models.chat_model import ChatModel

DB_PATH = Path(os.getenv("HOME")) / "dry_agent" / "database" / "dry_agent.db"

CHAT_QUERIES = aiosql.from_path(
    Path(__file__).parent.parent / "models/chat_model.sql",
    "sqlite3",
)


async def get_chat_model() -> AsyncGenerator[ChatModel, None]:
    """
    Yields a ChatModel backed by a fresh aiosqlite.Connection.
    """
    conn = await aiosqlite.connect(DB_PATH)
    conn.row_factory = aiosqlite.Row
    try:
        yield ChatModel(conn, CHAT_QUERIES)
    finally:
        await conn.close()
