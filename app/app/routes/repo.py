# app/routes/repo.py

import subprocess
from fastapi import APIRouter, HTTPException, status, Request
from fastapi.responses import PlainTextResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
GIT_REPO = "/root/git/vendor/enigmacurry/d.rymcg.tech"

@router.get("", response_class=HTMLResponse)
async def repo_page(request: Request):
    return templates.TemplateResponse("repo_page.html", {
        "request": request,
        "label": "pull d.rymcg.tech",
        "endpoint": "/app/repo/pull",
        "output_id": "git-output"
    })

@router.post("/pull", response_class=PlainTextResponse)
async def pull_repo():
    command = ["git", "-C", GIT_REPO, "pull"]
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=True
        )
        return f"## {' '.join(command)}\n\n" + result.stdout
    except subprocess.CalledProcessError as e:
        return PlainTextResponse(
            content=f"❌ Command failed: {' '.join(command)}\n\n{e.output}",
            status_code=500
        )
