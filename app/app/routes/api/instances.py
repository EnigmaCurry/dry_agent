from app.routes import DRY_COMMAND, DRY_PATH
from app.routes import api as api_routes
import logging
import os
from fastapi import APIRouter, Query, Request, HTTPException, Form
from fastapi.responses import JSONResponse
from pathlib import Path
from collections import defaultdict
from pydantic import BaseModel
from typing import Optional
from .lib import run_command, run_command_status, parse_env_file_contents
from .docker_context import get_docker_context_names
import json
import asyncio

"""
Manage app instances.
"""

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/api/instances", tags=["instances"])


class Instance(BaseModel):
    app: str
    env_path: Path
    context: str
    instance: str
    traefik_host: Optional[str]
    status: Optional[str]

    class Config:
        json_encoders = {Path: lambda v: str(v)}


def get_instances(
    include_status: bool = False,
    context: str | None = None,
    app: str | None = None,
) -> list[Instance]:
    valid_subdirs = (
        d for d in Path(DRY_PATH).iterdir() if d.is_dir() and d.name[:1].isalnum()
    )
    instances = []

    for subdir in valid_subdirs:
        app_name = subdir.name

        if app_name == "traefik":
            continue

        # Filter by app if specified
        if app and app_name != app:
            continue

        for env_file in subdir.glob(".env_*"):
            if not env_file.is_file():
                continue

            parts = env_file.name.split("_", 2)
            if len(parts) != 3:
                continue  # skip if not .env_{CONTEXT}_{INSTANCE}

            _, file_context, instance_name = parts

            # Filter by context if specified
            if context and file_context != context:
                continue

            with open(env_file, "r") as f:
                contents = f.read()
                env_dict, _, env_meta = parse_env_file_contents(contents)
                env_meta.setdefault("PREFIX", app_name.replace("-", "_").upper())
                try:
                    traefik_host = env_dict[f"{env_meta['PREFIX']}_TRAEFIK_HOST"]
                except KeyError:
                    traefik_host = None

            if include_status:
                try:
                    status_command = [
                        DRY_COMMAND,
                        "make",
                        app_name,
                        "docker-compose-lifecycle-cmd",
                        "EXTRA_ARGS=ps -a --format json",
                        "instance=" + instance_name,
                    ]
                    logger.debug(status_command)
                    status_output = run_command(status_command)
                    status_json = json.loads(status_output)
                except HTTPException:
                    status = "uninstalled"
                except json.JSONDecodeError as e:
                    if status_output.strip() == "":
                        status = "uninstalled"
                    else:
                        status = "error"
                        logger.error(e)
                else:
                    status = status_json.get("State", None)
            else:
                status = None

            instance_obj = Instance(
                app=app_name,
                env_path=env_file,
                context=file_context,
                instance=instance_name,
                traefik_host=traefik_host,
                status=status,
            )
            instances.append(instance_obj)

    return instances


@router.get("/", response_class=JSONResponse)
async def get_app_instances(
    context: Optional[str] = Query(default=None),
    app: Optional[str] = Query(default=None),
    include_status: Optional[bool] = Query(default=False),
):
    if context is None:
        context = run_command(["docker", "context", "show"]).strip()
    else:
        if context not in get_docker_context_names():
            return JSONResponse(
                content={"message": f"Context not found: {context}"}, status_code=404
            )

    instances = defaultdict(list)

    for instance in get_instances(
        include_status=include_status, context=context, app=app
    ):
        instances[instance.app].append(json.loads(instance.json()))

    return JSONResponse(content={context: instances})


@router.post("/config", response_class=JSONResponse)
async def save_instance_config(
    app: str = Form(...),
    context: str = Form(...),
    request: Request = None,
):
    form = await request.form()
    if not app or not context:
        raise HTTPException(status_code=400, detail="Missing 'app' or 'context'")

    data = await api_routes.env_dist.get_env_dist_data(app)
    prefix = data["meta"]["PREFIX"]

    # Parse {APP}_INSTANCE from .env posted to get the instance name
    instance_key = f"{prefix}_INSTANCE"
    instance = form.get(instance_key, "default").strip()

    env_filename = f".env_{context}_{instance}"
    env_path = os.path.join(DRY_PATH, app, env_filename)

    env_lines = []
    for key, value in form.items():
        if key == "app" or key == "context":
            continue
        env_lines.append(f"{key}={value}")
    env_lines.append(f"{instance_key}={instance}")

    try:
        with open(env_path, "w") as f:
            f.write("\n".join(env_lines) + "\n")

        return JSONResponse(
            content={
                "message": "Configuration saved",
                "env_file": env_filename,
                "app": app,
                "context": context,
                "instance": instance,
            },
            status_code=201,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write .env file: {e}")


@router.get("/config", response_class=JSONResponse)
async def get_instance_config(env_path=Query()):
    if not os.path.isfile(env_path):
        raise HTTPException(status_code=404, detail=f".env file not found: {env_path}")

    try:
        with open(env_path, "r") as f:
            contents = f.read()
            env_dict, _, _ = parse_env_file_contents(contents)

            return {"env": {key: env_dict[key] for key in env_dict}}

    except HTTPException:
        raise  # re-raise original HTTPException untouched
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
