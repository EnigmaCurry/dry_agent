# app/api/llm_context.py

from app.routes.api.docker_context import get_docker_context, get_docker_context_names
from app.routes.api.d_rymcg_tech import get_root_config, ConfigError
from app.routes.api.projects import get_available_projects
from app.routes.api.instances import get_instances
from typing import NamedTuple
import logging
import os
from typing import Optional
from openai import AsyncOpenAI
from pathlib import Path
import textwrap

logger = logging.getLogger(__name__)


class SystemConfig(NamedTuple):
    system_message: dict
    tool_spec: dict | None
    current_working_directory: Path


client = AsyncOpenAI(api_key="not needed", base_url=os.environ["OPENAI_BASE_URL"])

STATIC_SYSTEM_PROMPT = """\
You are dry_agent, a helpful assistant who manages Docker Compose projects.
You’re embedded in a web-app and a workstation environment.

Whenever you need the _current_ Docker state (context, projects, instances,
root domain, working directory), call the `get_docker_state()` function.

If the user asks you to switch contexts or start/stop apps, call the
appropriate function (`set_default_context` or `control_docker_project`).

Do not mention Docker Swarm or Kubernetes.
"""


async def get_docker_state_func() -> dict:
    # current context
    ctx = get_docker_context()
    # all contexts
    all_ctx = get_docker_context_names()
    # root domain (if configured)
    try:
        root_cfg = get_root_config(ctx)
        root_domain = root_cfg.get("ROOT_DOMAIN", None)
    except ConfigError:
        root_domain = None

    # available projects & installed instances
    projects = await get_available_projects()
    instances = get_instances(include_status=True)

    return {
        "docker_context": ctx,
        "root_domain": root_domain,
        "contexts": all_ctx,
        "projects": [p["name"] for p in projects],
        "instances": sorted(
            [inst.instance for inst in instances.values()],
            key=lambda i: (i != "default", i),
        ),
    }


async def get_system_config(current_working_directory: Optional[str]) -> SystemConfig:
    if current_working_directory:
        if os.path.isdir(current_working_directory):
            current_working_directory = Path(current_working_directory)
        else:
            raise ValueError(
                f"Invalid current working directory: {current_working_directory}"
            )
    all_contexts = get_docker_context_names()
    available_projects = await get_available_projects()

    # Gather known project and instance names
    project_names = [app["name"] for app in available_projects]

    if len(all_contexts) == 0:
        return SystemConfig(
            system_message={
                "role": "system",
                "content": """You are a helpful assistant for managing
                    Docker Compose projects, but you have been misconfigured
                    and do not have access to any configured Docker
                    contexts. Inform the user they must first create a
                    Docker context and set a root config before using
                    this assistant. """,
            },
            tool_spec=None,
            current_working_directory=current_working_directory,
        )

    # Define available tools
    tool_spec = [
        {
            "type": "function",
            "function": {
                "name": "get_docker_state",
                "description": textwrap.dedent(
                    """
                Returns JSON with the following structure:

                 * docker_context: the name of the current Docker
                   context.
                 * root_domain: the base domain name of the current
                   context.
                 * contexts: the list of all Docker contexts, that
                   could be switched to.
                 * projects: the list of all available Docker
                   projects, that you could choose to install. This
                   list does not indicate whether they are currently
                   running.
                 * instances: the list of all instance names used
                   amongst the configured projects.
                """
                ),
                "parameters": {"type": "object", "properties": {}},
                "required": [],
            },
        },
        {
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
        },
        {
            "type": "function",
            "function": {
                "name": "control_docker_project",
                "description": "Start or stop a Docker project by name.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "description": "The action to perform on the project. Must be 'start' or 'stop'.",
                            "enum": ["start", "stop"],
                        },
                        "project": {
                            "type": "string",
                            "description": "The name of the Docker project to control.",
                        },
                        "instance": {
                            "type": "string",
                            "description": "The instance of the Docker project to control.",
                        },
                    },
                    "required": ["action", "project", "instance"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "projects_status",
                "description": "Get the current status of all Docker compose projects",
            },
        },
        {
            "type": "function",
            "function": {
                "name": "open_app",
                "description": "Navigate the user to a specific page in dry_agent.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "page": {
                            "type": "string",
                            "description": "The name of the application page to navigate to.",
                            "enum": [
                                "settings",
                                "workstation",
                                "docker",
                                "repository",
                                "config",
                            ],
                        }
                    },
                    "required": ["page"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "open_instances",
                "description": "Navigate the user to the app instances page in dry_agent.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "app": {
                            "type": "string",
                            "description": "The name of the application page to navigate to.",
                            "enum": project_names,
                        }
                    },
                    "required": ["page"],
                },
            },
        },
    ]

    system_message = {"role": "system", "content": STATIC_SYSTEM_PROMPT}

    return SystemConfig(
        system_message=system_message,
        tool_spec=tool_spec,
        current_working_directory=current_working_directory,
    )


async def generate_title(
    message: str,
    model: str = "lite",
    max_tokens: int = 10,
    temperature: float = 0.5,
) -> str:
    """
    Generate a concise title summarizing the input message.

    Uses the AsyncOpenAI client (no need to set api_key in code
    if you've exported OPENAI_API_KEY or set up your config file).

    Args:
        message:      Text to summarize.
        model:        Model name.
        max_tokens:   Max tokens for the title.
        temperature:  Sampling temperature.

    Returns:
        One-line title.
    """
    resp = await client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant that writes very short titles.",
            },
            {
                "role": "user",
                "content": (
                    "Create a brief title (≤5 words) summarizing the following:\n\n"
                    f"{message}"
                ),
            },
        ],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    # strip quotes/newlines
    return resp.choices[0].message.content.strip().strip('"“”')
