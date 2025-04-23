from app.routes import DRY_PATH, DRY_COMMAND
from app.routes import api as api_routes
import logging
import os
import re
import traceback
import subprocess
from fastapi import APIRouter, Request, HTTPException, Form
from fastapi.responses import JSONResponse
from .lib import run_command

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/api/d.rymcg.tech", tags=["d.rymcg.tech"])


@router.get("/config", response_class=JSONResponse)
async def config(context: str = None):
    if not context:
        context = run_command(["docker", "context", "show"])
    config_path = os.path.join(DRY_PATH, f".env_{context}")
    if os.path.isfile(config_path):
        return JSONResponse({"context": context, "config_path": config_path})
    else:
        raise HTTPException(
            status_code=404,
            detail={"context": context, "message": "Config file not found"},
        )
