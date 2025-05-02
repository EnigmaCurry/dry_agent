# app/api/llm_context.py

from app.routes.api.docker_context import get_docker_context, get_docker_context_names
from app.routes.api.d_rymcg_tech import get_root_config, ConfigError
from app.routes.api.apps import get_available_apps
from typing import NamedTuple
import logging
from jinja2 import Template
import os

logger = logging.getLogger(__name__)

with open(os.path.join(os.path.dirname(__file__), "system_prompt.jinja2")) as f:
    SYSTEM_TEMPLATE = f.read()


class SystemConfig(NamedTuple):
    system_message: dict
    tool_spec: dict | None


async def get_system_config() -> SystemConfig:
    docker_context = get_docker_context()
    all_contexts = get_docker_context_names()
    available_apps = await get_available_apps()

    if len(all_contexts) == 0:
        return SystemConfig(
            system_message={
                "role": "system",
                "content": """You are a helpful assistant for managing
                    Docker services, but you have been misconfigured
                    and do not have access to any configured Docker
                    contexts. Inform the user they must first create a
                    Docker context and set a root config before using
                    this assistant. """,
            },
            tool_spec=None,
        )

    try:
        root_config = get_root_config(docker_context)
        root_domain = root_config.get("ROOT_DOMAIN", "unknown")
    except ConfigError:
        root_config = None
        root_domain = None

    tool_spec = {
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
                        "enum": all_contexts if all_contexts is not None else [],
                    }
                },
                "required": ["context"],
            },
        },
    }

    template = Template(SYSTEM_TEMPLATE)
    content = template.render(
        context_message=(
            f"for the current Docker context named '{docker_context}'"
            if docker_context
            else ""
        ),
        root_domain=root_domain,
        other_contexts_message=", ".join(all_contexts) if all_contexts else "",
        available_apps=", ".join(app["name"] for app in available_apps),
    )

    system_message = {"role": "system", "content": content}
    logger.info(system_message)
    return SystemConfig(system_message=system_message, tool_spec=tool_spec)
