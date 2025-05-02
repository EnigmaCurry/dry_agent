import logging
from fastapi import APIRouter, Depends, Request, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
import openai
from typing import AsyncGenerator

from .lib import run_command
from .docker_context import (
    get_docker_context_names,
    get_docker_context,
    set_default_context,
)
from .d_rymcg_tech import get_root_config, ConfigError
from app.lib.db import get_chat_model, ChatModel
from app.broadcast import broadcast
from .llm_util import generate_title

"""
LLM Chat API
"""

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/api/chat", tags=["chat"])

client = openai.AsyncOpenAI()

set_context_tool = {
    "type": "function",
    "function": {
        "name": "set_default_context",
        "description": "Switch the current Docker context",
        "parameters": {
            "type": "object",
            "properties": {
                "context": {
                    "type": "string",
                    "description": "The name of the Docker context to switch to",
                }
            },
            "required": ["context"],
        },
    },
}


@router.post("/stream/{conversation_id}")
async def stream_chat(
    conversation_id: str,
    request: Request,
    chat: ChatModel = Depends(get_chat_model),
) -> StreamingResponse:
    body = await request.json()
    user_message = body.get("message", None)

    if not isinstance(user_message, str):
        raise HTTPException(status_code=422, detail="`message` must be a string")

    conversation = await chat.get_conversation(conversation_id)
    if conversation is None:
        summary_title = await generate_title(user_message)
        await chat.create_conversation(conversation_id, title=summary_title)
        conversation = []
        logger.info(f"Created new conversation: {conversation_id}")
    else:
        logger.info(f"Found existing conversation: {conversation_id}")

    await chat.add_message(conversation_id, "user", user_message)
    logger.info(f"User: {user_message}")

    if isinstance(conversation, dict):
        messages = conversation.get("messages", [])
    else:
        messages = conversation

    # 🧠 Inject dynamic system message
    docker_context = get_docker_context()
    all_contexts = get_docker_context_names()
    try:
        root_config = get_root_config(docker_context)
    except ConfigError:
        root_config = {}

    try:
        root_domain = root_config["ROOT_DOMAIN"]
    except KeyError:
        root_domain = None

    if root_config == {}:
        system_message = {
            "role": "system",
            "content": f"""You are a helpful assistant for managing
            Docker services, except you have been misconfigured and
            you do not have access to any configured Docker contexts.
            If the user asks you to perform any actions, kindly inform
            them that they must first create a new Docker context.""",
        }
    else:
        system_message = {
            "role": "system",
            "content": f"""You are a helpful assistant managing Docker
            services for the current Docker context named
            '{docker_context}'. This context is a single Docker node
            running Traefik and capable of running various other services.
            The default root domain name configured for use by the
            services is '{root_domain}'.

            You can also potentially manage other contexts after switching
            to them: {all_contexts}

            Do not ever discuss (or even mention) Docker Swarm or
            Kubernetes as these topics are irrelevant and will only lead
            to confusion. Please answer any questions accordingly. When
            presenting information related to the specific Docker context,
            domain names, or service configurations, please prefer to
            provide these as consise bulleted lists. """,
        }

    messages = [system_message] + messages + [{"role": "user", "content": user_message}]

    response_text = ""

    async def generate() -> AsyncGenerator[str, None]:
        nonlocal response_text
        tool_call_args = ""

        try:
            stream = await client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                stream=True,
                tools=[set_context_tool],
                tool_choice="auto",
            )

            async for chunk in stream:
                choice = chunk.choices[0]
                if choice.finish_reason == "tool_calls":
                    continue
                if choice.delta.tool_calls:
                    for tool_call in choice.delta.tool_calls:
                        tool_call_args += tool_call.function.arguments or ""
                elif choice.delta.content is not None:
                    delta = choice.delta.content
                    response_text += delta
                    yield delta

            if tool_call_args:
                import json

                args = json.loads(tool_call_args)
                context_name = args["context"]
                valid_contexts = get_docker_context_names()

                if context_name not in valid_contexts:
                    msg = f"\n\n❌ Error: '{context_name}' is not a valid Docker context.\nAvailable contexts: {valid_contexts}"
                    logger.warning(msg)
                    yield msg
                else:
                    set_default_context(context_name)
                    await broadcast(
                        {
                            "type": "context_changed",
                            "data": {"new_context": context_name},
                        }
                    )
                    logger.info(f"Switched Docker context to: {context_name}")
                    response_text += f"\n\n✅ Switched context to '{context_name}'"
                    yield response_text

            await chat.add_message(conversation_id, "assistant", response_text)
            logger.info(
                f"Logged new assistant message in conversation: {conversation_id}"
            )

        except Exception as e:
            logger.error(f"OpenAI streaming error: {e}")
            yield "\n\n[ERROR: LLM request failed]\n"
            raise e

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


@router.delete("/conversation/{id}")
async def delete_conversation(id: str, chat_model: ChatModel = Depends(get_chat_model)):
    try:
        await chat_model.delete_conversation(conversation_id=id)
        return JSONResponse(content={"deleted": id})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
