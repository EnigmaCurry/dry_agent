# from app.routes import DRY_COMMAND, DRY_PATH
from app.routes import api as api_routes
import logging
from fastapi import APIRouter, Depends, Request, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
import openai
import os
import asyncio
from .lib import tokenize_words
from typing import AsyncGenerator
from pathlib import Path

from app.lib.db import get_chat_model, ChatModel

"""
LLM Chat API
"""

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/api/chat", tags=["chat"])

doc1: str = (Path(__file__).parent / "chat_example.md").read_text(encoding="utf-8")


@router.post("/stream/{conversation_id}")
async def stream_chat(
    conversation_id: str,
    request: Request,
    chat: ChatModel = Depends(get_chat_model),
) -> StreamingResponse:
    body = await request.json()
    user_message = body.get("message")
    if not isinstance(user_message, str):
        raise HTTPException(status_code=422, detail="`message` must be a string")

    # Fetch or create
    if await chat.get_conversation(conversation_id) is None:
        await chat.create_conversation(conversation_id)
        logger.info(f"Created new conversation: {conversation_id}")
    else:
        logger.info(f"Found existing conversation: {conversation_id}")

    # Record user message
    await chat.add_message(conversation_id, "user", user_message)
    logger.info(
        f"Logging new user message in conversation: {conversation_id} - {user_message}"
    )

    # Stream & record assistant reply
    response_text = ""

    async def generate() -> AsyncGenerator[str, None]:
        nonlocal response_text
        for token in tokenize_words(doc1):
            response_text += token
            yield token
            await asyncio.sleep(0.05)
        await chat.add_message(conversation_id, "assistant", response_text)
        logger.info(f"Logging new assistant message in conversation: {conversation_id}")

    return StreamingResponse(generate(), media_type="text/plain")
