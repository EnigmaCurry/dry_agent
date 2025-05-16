import logging
from fastapi import APIRouter, Depends, Request, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
import openai
from typing import AsyncGenerator, Callable
import json
import os

from .lib import run_command
from .docker_context import (
    get_docker_context_names,
    set_default_context,
)
from app.lib.db import get_chat_model, ChatModel
from app.broadcast import broadcast
from app.lib.llm_util import (
    get_docker_state_func,
    generate_title,
    get_system_config,
    SystemConfig,
)
from app.routes import DRY_COMMAND
from app.models.events import ContextChangedEvent, OpenAppEvent, OpenInstancesEvent
from pathlib import Path
from .projects import get_projects_status

"""
LLM Chat API
"""

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/api/chat", tags=["chat"])

client = openai.AsyncOpenAI(
    api_key="not needed", base_url=os.environ["OPENAI_BASE_URL"]
)


async def parse_request_body(request: Request) -> str:
    body = await request.json()
    user_message = body.get("message")
    current_working_directory = body.get("cwd")
    if not isinstance(user_message, str):
        raise HTTPException(status_code=422, detail="`message` must be a string")
    return user_message, current_working_directory


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


async def handle_tool_call(call, system_config: SystemConfig) -> str:
    function_name = call.function.name
    arguments = getattr(call, "parsed_arguments", {})
    logger.info(f"Tool call: function_name : {function_name} :: arguments: {arguments}")
    if function_name == "get_docker_state":
        state = await get_docker_state_func()
        state["current_working_directory"] = str(
            system_config.current_working_directory
        )
        return json.dumps(state)
    elif function_name == "set_default_context":
        context_name = arguments["context"]
        valid_contexts = get_docker_context_names()
        if context_name not in valid_contexts:
            msg = f"\n\n❌ Error: '{context_name}' is not a valid Docker context.\nAvailable contexts: {valid_contexts}"
            logger.warning(msg)
            return msg
        set_default_context(context_name)
        await broadcast(ContextChangedEvent(new_context=context_name))
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
    elif function_name == "open_app":
        page = arguments["page"]
        await broadcast(OpenAppEvent(page=page))
        msg = f"\n\n🧭 Opening {page.title()}"
        return msg
    elif function_name == "open_instances":
        app = arguments["app"]
        await broadcast(OpenInstancesEvent(app=app))
        msg = f"\n\n🧭 Opening instances page for {app}"
        return msg
    elif function_name == "projects_status":
        status = await get_projects_status()
        return json.dumps(status)

    msg = f"\n\n⚠️ Unknown tool called: {function_name}"
    logger.warning(msg)
    return msg


async def stream_llm_response(
    conversation_id: str, chat, messages: list[dict], system_config
) -> Callable[[], AsyncGenerator[str, None]]:
    """
    Returns an async generator factory `generate()` that:
      1. Streams an initial chat completion pass, collecting any function calls.
      2. If functions were called:
         a) Executes them, appending their results as function‐role messages.
         b) Streams a second chat completion pass so the model can reason
            over the real JSON outputs and produce a final, user‐facing reply.
      3. If no functions were called, just finishes after phase 1.
    """

    async def generate():
        nonlocal messages
        response_text = ""
        collected_tool_calls: dict[int, dict] = {}
        saw_tool_call = False

        # ── PHASE 1: initial streaming with tools enabled ────────────────────
        try:
            stream1 = await client.chat.completions.create(
                model="assistant",
                messages=messages,
                stream=True,
                tools=system_config.tool_spec,
                tool_choice="auto" if system_config.tool_spec else None,
            )

            async for chunk in stream1:
                choice = chunk.choices[0]
                # 1a) collect function_call fragments
                if choice.delta.tool_calls:
                    saw_tool_call = True
                    for tc in choice.delta.tool_calls:
                        idx = tc.index
                        spot = collected_tool_calls.setdefault(
                            idx,
                            {"id": tc.id, "name": None, "arguments": ""},
                        )
                        if tc.id and not spot["id"]:
                            spot["id"] = tc.id
                        fn = getattr(tc, "function", None)
                        if fn:
                            if fn.name:
                                spot["name"] = fn.name
                            if fn.arguments:
                                spot["arguments"] += fn.arguments
                    continue

                # 1b) otherwise stream any actual assistant text
                if choice.delta.content:
                    response_text += choice.delta.content
                    yield choice.delta.content

        except Exception:
            logger.exception("Phase 1 LLM streaming error")
            yield "\n\n[ERROR: initial LLM call failed]\n"
            return

        # ── If no function was called, finalize and return ────────────────
        if not saw_tool_call:
            await chat.add_message(conversation_id, "assistant", response_text)
            return

        # ── PHASE 1.5: execute each collected tool call ───────────────────
        for call in collected_tool_calls.values():
            name = call.get("name")
            raw_args = call.get("arguments", "")
            if not name or not raw_args.strip():
                continue

            try:
                parsed = json.loads(raw_args)
            except json.JSONDecodeError:
                parsed = {}

            # Build a fake OpenAI ToolCall object
            tool_call_obj = type(
                "ToolCall",
                (),
                {
                    "function": type("F", (), {"name": name, "arguments": raw_args})(),
                    "parsed_arguments": parsed,
                    "id": call.get("id"),
                },
            )
            # Execute the tool, get back either JSON (for get_docker_state)
            # or a user‐facing string (for set_default_context, etc.)
            result = await handle_tool_call(tool_call_obj, system_config)

            # Inject that result into the convo so the model can see it
            messages.append(
                {
                    "role": "function",
                    "name": name,
                    "content": result,
                }
            )

        # ── PHASE 2: final streaming WITHOUT tools ─────────────────────────
        response_text = ""
        try:
            stream2 = await client.chat.completions.create(
                model="assistant",
                messages=messages,
                stream=True,
            )
            async for chunk in stream2:
                delta = chunk.choices[0].delta.content
                if delta:
                    response_text += delta
                    yield delta

        except Exception:
            logger.exception("Phase 2 LLM streaming error")
            yield "\n\n[ERROR: final LLM call failed]\n"
            return

        # ── Record the assistant’s final reply in the DB ─────────────────
        await chat.add_message(conversation_id, "assistant", response_text)

    return generate


@router.post("/stream/{conversation_id}")
async def stream_chat(
    conversation_id: str,
    request: Request,
    chat: ChatModel = Depends(get_chat_model),
) -> StreamingResponse:
    user_message, current_working_directory = await parse_request_body(request)

    conversation = await prepare_conversation(chat, conversation_id, user_message)

    system_config = await get_system_config(current_working_directory)

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
