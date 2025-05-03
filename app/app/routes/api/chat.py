import logging
from fastapi import APIRouter, Depends, Request, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
import openai
from typing import AsyncGenerator, Callable
import json

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
from app.lib.llm_util import get_system_config, SystemConfig
from app.routes import DRY_COMMAND

"""
LLM Chat API
"""

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/api/chat", tags=["chat"])

client = openai.AsyncOpenAI()


async def parse_request_body(request: Request) -> str:
    body = await request.json()
    user_message = body.get("message")
    if not isinstance(user_message, str):
        raise HTTPException(status_code=422, detail="`message` must be a string")
    return user_message


async def prepare_conversation(
    chat: ChatModel, conversation_id: str, user_message: str
) -> list:
    conversation = await chat.get_conversation(conversation_id)
    if conversation is None:
        summary_title = await generate_title(user_message)
        await chat.create_conversation(conversation_id, title=summary_title)
        conversation = []
        logger.info(f"Created new conversation: {conversation_id}")
    else:
        logger.info(f"Found existing conversation: {conversation_id}")

    await chat.add_message(conversation_id, "user", user_message)
    return (
        conversation.get("messages", [])
        if isinstance(conversation, dict)
        else conversation
    )


def prepare_messages(
    system_config: SystemConfig, messages: list, user_message: str
) -> list:
    return (
        [system_config.system_message]
        + messages
        + [{"role": "user", "content": user_message}]
    )


async def handle_tool_call(call) -> str:
    function_name = call.function.name
    arguments = getattr(call, "parsed_arguments", {})
    logger.info(f"Tool call: function_name : {function_name} :: arguments: {arguments}")
    if function_name == "set_default_context":
        context_name = arguments["context"]
        valid_contexts = get_docker_context_names()
        if context_name not in valid_contexts:
            msg = f"\n\n❌ Error: '{context_name}' is not a valid Docker context.\nAvailable contexts: {valid_contexts}"
            logger.warning(msg)
            return msg
        set_default_context(context_name)
        await broadcast(
            {"type": "context_changed", "data": {"new_context": context_name}}
        )
        logger.info(f"Switched Docker context to: {context_name}")
        return f"\n\n✅ Switched context to '{context_name}'"

    elif function_name == "control_docker_project":
        action = arguments["action"]
        project = arguments["project"]
        instance = arguments["instance"]
        try:
            command = [DRY_COMMAND, "make", project, action, f"instance={instance}"]
            run_command(command)
            msg = f"\n\n✅ Successfully ran: {' '.join(command)}"
            logger.info(msg.strip())
            return msg
        except Exception as e:
            msg = f"\n\n❌ Failed to {action} project '{project} instance '{instance}': {e}"
            logger.error(msg)
            return msg

    msg = f"\n\n⚠️ Unknown tool called: {function_name}"
    logger.warning(msg)
    return msg


async def stream_llm_response(
    conversation_id, chat, messages, system_config
) -> Callable:
    response_text = ""
    collected_tool_calls: dict[str, dict] = {}

    async def generate():
        nonlocal response_text

        try:
            stream = await client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                stream=True,
                tools=system_config.tool_spec,
                tool_choice="auto" if system_config.tool_spec else None,
            )

            async for chunk in stream:
                choice = chunk.choices[0]

                # 🧩 Accumulate tool call fragments by ID
                if choice.delta.tool_calls:
                    for tc in choice.delta.tool_calls:
                        index = tc.index
                        existing = collected_tool_calls.setdefault(
                            index,
                            {
                                "id": tc.id,  # may only be valid on first chunk
                                "name": None,
                                "arguments": "",
                            },
                        )

                        if tc.id and not existing["id"]:
                            existing["id"] = tc.id

                        function = getattr(tc, "function", None)
                        if function:
                            if function.name:
                                existing["name"] = function.name
                            if function.arguments:
                                existing["arguments"] += function.arguments
                    continue

                # 💬 Accumulate assistant text output
                if choice.delta.content:
                    delta = choice.delta.content
                    response_text += delta
                    yield delta

            # 🛠 Execute completed tool calls
            for call in collected_tool_calls.values():
                name = call.get("name")
                raw_args = call.get("arguments", "")

                if not name:
                    msg = f"\n\n⚠️ Skipping tool call {call.get('id')} — missing function name."
                    logger.warning(msg)
                    yield msg
                    continue

                if not raw_args.strip():
                    msg = f"\n\n❌ Skipping tool `{name}` — no arguments received."
                    logger.error(msg)
                    yield msg
                    continue

                try:
                    parsed_args = json.loads(raw_args)
                except json.JSONDecodeError as e:
                    msg = f"\n\n❌ Failed to parse arguments for tool `{name}`: {e}"
                    logger.error(msg)
                    yield msg
                    continue

                # Simulate OpenAI-style tool call object
                tool_call_obj = type(
                    "ToolCall",
                    (),
                    {
                        "function": type(
                            "Function",
                            (),
                            {
                                "name": name,
                                "arguments": raw_args,
                            },
                        )(),
                        "id": call["id"],
                        "parsed_arguments": parsed_args,
                    },
                )

                tool_result = await handle_tool_call(tool_call_obj)
                response_text += tool_result
                yield tool_result

            await chat.add_message(conversation_id, "assistant", response_text)
            logger.info(f"Logged assistant message to {conversation_id}")

        except Exception as e:
            logger.exception("OpenAI streaming error")
            yield "\n\n[ERROR: LLM request failed]\n"
            raise e

    return generate


@router.post("/stream/{conversation_id}")
async def stream_chat(
    conversation_id: str,
    request: Request,
    chat: ChatModel = Depends(get_chat_model),
) -> StreamingResponse:
    user_message = await parse_request_body(request)

    conversation = await prepare_conversation(chat, conversation_id, user_message)

    system_config = await get_system_config()

    messages = prepare_messages(system_config, conversation, user_message)

    generate = await stream_llm_response(conversation_id, chat, messages, system_config)

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
