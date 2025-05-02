# app/api/llm_context.py

from app.routes.api.docker_context import get_docker_context, get_docker_context_names
from app.routes.api.d_rymcg_tech import get_root_config, ConfigError


def get_context_tool():
    return {
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


def get_system_message() -> dict:
    docker_context = get_docker_context()
    all_contexts = get_docker_context_names()

    try:
        root_config = get_root_config(docker_context)
    except ConfigError:
        return {
            "role": "system",
            "content": (
                "You are a helpful assistant for managing Docker services, but you have "
                "been misconfigured and do not have access to any configured Docker contexts. "
                "Inform the user they must first create a Docker context before using this assistant."
            ),
        }

    root_domain = root_config.get("ROOT_DOMAIN", "unknown")

    return {
        "role": "system",
        "content": (
            f"You are a helpful assistant managing Docker services for the current Docker context "
            f"named '{docker_context}'. This context is a single Docker node running Traefik "
            f"and other services. The default root domain name is '{root_domain}'.\n\n"
            f"You can also manage other contexts: {all_contexts}\n\n"
            "- Do not mention Docker Swarm or Kubernetes\n"
            "- Use concise bulleted lists when sharing config/domain info\n"
        ),
    }
