import os
import re
import subprocess
from fastapi import APIRouter, HTTPException, status, Request
from fastapi.responses import PlainTextResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Tuple, Dict

DRY_PATH = os.path.expanduser("~/git/vendor/enigmacurry/d.rymcg.tech")
DRY_COMMAND = os.path.join(DRY_PATH, "_scripts/d.rymcg.tech")
