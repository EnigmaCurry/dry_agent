import uuid
from pathlib import Path
from typing import List, Optional
import aiosqlite
import logging

logger = logging.getLogger(__name__)


class ChatModel:
    def __init__(self, conn: aiosqlite.Connection, queries):
        self.conn = conn
        self.queries = queries

    async def create_conversation(self, conversation_id: Optional[str] = None) -> str:
        conv_id = conversation_id or str(uuid.uuid4())
        await self.queries.create_conversation(conn=self.conn, id=conv_id)
        await self.conn.commit()
        return conv_id

    async def get_conversation(self, conversation_id: str) -> Optional[dict]:
        logger.info(f"conn type: {type(self.conn)}")
        logger.info(await self.conn.execute("SELECT 1"))
        logger.info(type(await self.conn.execute("SELECT 1")))
        row = await self.queries.get_conversation(conn=self.conn, id=conversation_id)
        return dict(row) if row else None

    async def add_message(self, conversation_id: str, role: str, content: str) -> None:
        await self.queries.add_message(
            conn=self.conn,
            conversation_id=conversation_id,
            role=role,
            content=content,
        )
        await self.conn.commit()

    async def get_last_messages(
        self, conversation_id: str, limit: int = 20
    ) -> list[dict]:
        rows = await self.queries.get_last_messages(
            conn=self.conn,
            conversation_id=conversation_id,
            limit=limit,
        )
        return [dict(r) for r in rows]
