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
            conn.row_factory = aiosqlite.Row
            rows = await self.queries.get_conversation_with_messages(
                conn=conn, id=conversation_id
            )

        if not rows:
            return None

        # Extract conversation metadata from the first row
        first = rows[0]
        conversation = {
            "id": first["conversation_id"],
            "title": first["conversation_title"],
            "created_at": first["conversation_created_at"],
            "messages": [
                {
                    "role": row["message_role"],
                    "content": row["message_content"],
                    "created_at": row["message_created_at"],
                }
                for row in rows
                if row["message_role"] is not None
            ],
        }

        return conversation

    async def add_message(self, conversation_id: str, role: str, content: str) -> None:
        async with self.connection() as conn:
            await self.queries.add_message(
                conn=conn,
                conversation_id=conversation_id,
                role=role,
                content=content,
            )
            await conn.commit()

    async def get_conversations_paginated(
        self, offset: int = 0, page_size: int = 10
    ) -> List[dict]:
        async with self.connection() as conn:
            conn.row_factory = aiosqlite.Row
            rows = await self.queries.get_conversations_with_first_sentence_paginated(
                conn=conn, offset=offset, page_size=page_size
            )
        return [dict(r) for r in rows]
