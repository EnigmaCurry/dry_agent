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

@router.get("/app/repo/branch", response_class=HTMLResponse)
async def repo_branch(request: Request):
    try:
        branches = get_git_branches(DRY_PATH)
        current_branch = get_current_git_branch(DRY_PATH)

        return templates.TemplateResponse("repo_branch.html", {
            "request": request,
            "branches": branches,
            "current_branch": current_branch,
        })

    except Exception as e:
        return HTMLResponse(
            content=f"<p class='has-text-danger'>❌ Failed to load branches:<br><pre>{e}</pre></p>",
            status_code=500
        )

@router.post("/api/repo/checkout", response_class=PlainTextResponse)
async def checkout_branch(branch: str = Form(...)):
    try:
        result = subprocess.run(
            ["git", "-C", DRY_PATH, "checkout", branch],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=e.output)

def get_git_branches(repo_path: str) -> List[str]:
    """
    Returns a sorted list of unique local and remote Git branches.
    Removes duplicates and 'HEAD' reference from remotes.
    """
    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "branch", "-a", "--format=%(refname:short)"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )

        raw_branches = result.stdout.strip().splitlines()

        branches = set()
        for branch in raw_branches:
            branch = branch.strip()

            # Skip HEAD and empty lines
            if not branch or branch.endswith("HEAD"):
                continue

            # Normalize remote refs: "remotes/origin/branch" → "origin/branch"
            if branch.startswith("remotes/"):
                branch = branch.replace("remotes/", "", 1)

            branches.add(branch)

        return sorted(branches)

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to get branches: {e.stderr.strip()}")

def get_current_git_branch(repo_path: str) -> str:
    """
    Returns the current checked-out branch name.
    If in detached HEAD state, returns something like:
    '(HEAD detached at origin/acme-dns)'
    """
    try:
        # First, try getting the branch name
        result = subprocess.run(
            ["git", "-C", repo_path, "symbolic-ref", "--short", "HEAD"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True
        )

        if result.returncode == 0:
            return result.stdout.strip()

        # Detached HEAD — get the current commit
        result = subprocess.run(
            ["git", "-C", repo_path, "rev-parse", "--short", "HEAD"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=True
        )
        short_commit = result.stdout.strip()

        # Try to find remote branch pointing to the same commit
        result = subprocess.run(
            ["git", "-C", repo_path, "branch", "-r", "--contains", short_commit],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        remotes = result.stdout.strip().splitlines()
        remotes = [r.strip() for r in remotes if r.strip()]

        if remotes:
            return f"(HEAD detached at {remotes[0]})"
        else:
            return f"(HEAD detached at {short_commit})"

    except subprocess.CalledProcessError:
        return "(unknown)"
