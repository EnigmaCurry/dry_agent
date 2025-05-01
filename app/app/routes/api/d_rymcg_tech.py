from app.routes import DRY_PATH, DRY_COMMAND
from app.routes import api as api_routes
import logging
import os
import re
import traceback
import subprocess
from fastapi import APIRouter, Request, HTTPException, Form
from fastapi.responses import JSONResponse
from .lib import run_command, parse_env_file_contents

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/api/d.rymcg.tech", tags=["d.rymcg.tech"])


class ConfigError(Exception):
    pass


def get_root_config(context: str = None):
    if not context:
        context = run_command(["docker", "context", "show"])
    config_path = os.path.join(DRY_PATH, f".env_{context}")
    if os.path.isfile(config_path):
        with open(config_path) as f:
            contents = f.read()
            env_dict, _, _ = parse_env_file_contents(contents)
            return env_dict
    else:
        raise ConfigError("Config file not found: {config_path}")


@router.get("/config", response_class=JSONResponse)
async def config(context: str = None):
    if not context:
        context = run_command(["docker", "context", "show"])
    try:
        return get_root_config(context)
    except ConfigError:
        raise HTTPException(
            status_code=404,
            detail={"context": context, "message": "Config file not found"},
        )
