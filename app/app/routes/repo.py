from app.routes import *

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/app/repo/pull", response_class=HTMLResponse)
async def repo_page(request: Request):
    return templates.TemplateResponse("repo_pull.html", {
        "request": request,
        "label": "Pull d.rymcg.tech",
        "endpoint": "/api/repo/pull",
        "output_id": "git-output"
    })

@router.post("/api/repo/pull", response_class=PlainTextResponse)
async def pull_repo():
    command = ["git", "-C", DRY_PATH, "pull"]
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
