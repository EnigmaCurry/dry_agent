# Modified version of app/app/models/chat_model.py
import uuid
from pathlib import Path
from typing import List, Optional, Callable, AsyncContextManager
import aiosqlite
import logging
from gibberish import Gibberish

logger = logging.getLogger(__name__)

gib = Gibberish()


class ChatModel:
    def __init__(
        self,
        conn_provider: Callable[[], AsyncContextManager[aiosqlite.Connection]],
        queries,
    ):
        self.connection = conn_provider
        self.queries = queries

    async def create_conversation(
        self, conversation_id: Optional[str] = None, title: Optional[str] = None
    ) -> str:
        conv_id = conversation_id or str(uuid.uuid4())
        title = title or " ".join(gib.generate_words(2)).title()
        async with self.connection() as conn:
            await self.queries.create_conversation(conn=conn, id=conv_id, title=title)
            await conn.commit()
        return conv_id

    async def get_conversation(self, conversation_id: str) -> Optional[dict]:
        async with self.connection() as conn:
            row = await self.queries.get_conversation(conn=conn, id=conversation_id)
        return dict(row) if row else None

    async def add_message(self, conversation_id: str, role: str, content: str) -> None:
        async with self.connection() as conn:
            await self.queries.add_message(
                conn=conn,
                conversation_id=conversation_id,
                role=role,
                content=content,
            )
            await conn.commit()

    async def get_last_messages(
        self, conversation_id: str, limit: int = 20
    ) -> List[dict]:
        async with self.connection() as conn:
            rows = await self.queries.get_last_messages(
                conn=conn,
                conversation_id=conversation_id,
                limit=limit,
            )
        return [dict(r) for r in rows]
