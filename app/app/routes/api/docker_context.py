import os
from typing import List
from fastapi import APIRouter, HTTPException
import json
from .lib import run_command

# Import the parse_ssh_config from the sibling module.
from .ssh_config import parse_ssh_config

router = APIRouter(prefix="/api/docker_context", tags=["docker_context"])


def get_docker_context_names() -> List[str]:
    """
    Retrieve a list of existing docker context names.
    """
    output = run_command(["docker", "context", "ls", "--format", "{{.Name}}"])
    # Each line represents a context name.
    if output:
        return output.splitlines()
    return []


@router.get("/", response_model=List[str])
def get_all_contexts():
    """
    Retrieve all docker contexts using the docker CLI.
    """
    contexts = get_docker_context_names()
    return contexts


@router.post("/", response_model=dict)
def create_context(context_name: str):
    """
    Create a new docker context using docker CLI commands.
    Validates that the context does not already exist and that the SSH config entry exists.
    """
    # Check if the context already exists.
    if context_name in get_docker_context_names():
        raise HTTPException(status_code=400, detail="Context already exists.")

    # Validate SSH config entry.
    ssh_config_path = os.path.expanduser("~/.ssh/config")
    try:
        hosts = parse_ssh_config(ssh_config_path)
    except FileNotFoundError:
        raise HTTPException(
            status_code=400, detail=f"SSH config not found at {ssh_config_path}"
        )

    entry_exists = False
    for host_entry in hosts:
        if "Host" in host_entry and context_name in host_entry["Host"]:
            entry_exists = True
            break

    if not entry_exists:
        raise HTTPException(status_code=400, detail="SSH config entry does not exist.")

    # Create the new context using docker context create.
    cmd = [
        "docker",
        "context",
        "create",
        context_name,
        "--docker",
        f"host=ssh://{context_name}",
    ]
    run_command(cmd)
    return {"detail": f"Context '{context_name}' created successfully."}


@router.delete("/{context_name}", response_model=dict)
def delete_context(context_name: str):
    """
    _    Delete an existing docker context using the docker CLI.
    """
    # Check if the context exists.
    if context_name not in get_docker_context_names():
        raise HTTPException(status_code=404, detail="Context not found.")

    cmd = ["docker", "context", "rm", "-f", context_name]
    run_command(cmd)
    return {"detail": f"Context '{context_name}' deleted successfully."}


@router.put("/{context_name}/default", response_model=dict)
def set_default_context(context_name: str):
    """
    Set an existing docker context as the default using the docker CLI.
    """
    if context_name not in get_docker_context_names():
        raise HTTPException(status_code=404, detail="Context not found.")

    cmd = ["docker", "context", "use", context_name]
    run_command(cmd)
    return {"detail": f"Context '{context_name}' set as default."}


@router.get("/default", response_model=dict)
def get_default_context():
    """
    Retrieve the current default docker context using the docker CLI.
    """
    default_context = run_command(["docker", "context", "show"])
    return {"default_context": default_context}


def get_context_from_docker_info_json_for_context(context_name: str) -> str:
    """
    Call `docker info` with JSON formatting using the specified context.
    Uses a timeout of 5 seconds for the command.
    The JSON output is expected to contain a 'ClientInfo' key with a nested 'Context' key.
    """
    json_output = run_command(
        ["docker", "--context", context_name, "info", "--format", "{{json .}}"],
        timeout=5,
    )
    try:
        info = json.loads(json_output)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500, detail="Failed to parse docker info output as JSON."
        )

    client_info = info.get("ClientInfo", {})
    context = client_info.get("Context")
    if context is None:
        raise HTTPException(
            status_code=500,
            detail="Context information not found in docker info JSON output.",
        )
    return context


@router.get("/test/{context_name}", response_model=dict)
def test_docker_context(context_name: str):
    """
    Test that the specified docker context is working by calling `docker info`
    with JSON formatting using the user-specified context.
    Parses the JSON output and extracts the current context name from the ClientInfo key.
    This call will timeout after 5 seconds if docker info does not return in time.
    """
    # Check if the context exists.
    if context_name not in get_docker_context_names():
        raise HTTPException(status_code=404, detail="Context not found.")

    current_context = get_context_from_docker_info_json_for_context(context_name)
    return {"docker_context": current_context}
