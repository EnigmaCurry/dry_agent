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
doc2: str = (Path(__file__).parent / "chat_example2.md").read_text(encoding="utf-8")


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
        for token in tokenize_words(doc2):
            response_text += token
            yield token
            # await asyncio.sleep(0.05)
        await chat.add_message(conversation_id, "assistant", response_text)
        logger.info(f"Logging new assistant message in conversation: {conversation_id}")

    return StreamingResponse(generate(), media_type="text/plain")


@router.get("/conversations")
async def conversation_previews(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    chat_model: ChatModel = Depends(get_chat_model),
):
    offset = (page - 1) * page_size
    conversations = await chat_model.get_conversations_paginated(
        offset=offset, page_size=page_size
    )
    return {"page": page, "conversations": conversations}


@router.get("/conversation/{id}")
async def get_conversation(id: str, chat_model: ChatModel = Depends(get_chat_model)):
    try:
        conversation = await chat_model.get_conversation(conversation_id=id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return JSONResponse(content=conversation)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
