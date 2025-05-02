# app/api/llm_context.py

from app.routes.api.docker_context import get_docker_context, get_docker_context_names
from app.routes.api.d_rymcg_tech import get_root_config, ConfigError
from typing import NamedTuple


class SystemConfig(NamedTuple):
    system_message: dict
    tool_spec: dict | None


def get_system_config() -> SystemConfig:
    docker_context = get_docker_context()
    all_contexts = get_docker_context_names()

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

    root_domain_message = (
        "The default root domain name is '{root_domain}'"
        if root_domain is not None
        else ""
    )
    context_message = (
        f"for the current Docker context named '{docker_context}'"
        if docker_context is not None
        else ""
    )
    other_contexts_message = (
        f"You can also manage other contexts: {all_contexts}"
        if len(all_contexts)
        else ""
    )

    system_message = {
        "role": "system",
        "content": (
            f"You are a helpful assistant managing Docker services {context_message}."
            " This context is a single Docker node running Traefik "
            f"and other services. {root_domain_message}.\n\n"
            f"{other_contexts_message}\n\n"
            "- Do not mention Docker Swarm or Kubernetes\n"
            "- Use concise bulleted lists when sharing config/domain info\n"
        ),
    }

    return SystemConfig(system_message=system_message, tool_spec=tool_spec)
