from fastapi import APIRouter, HTTPException, Form
from fastapi.responses import JSONResponse
from typing import List

from app.routes import DRY_PATH
from .lib import run_command

router = APIRouter()
router = APIRouter(prefix="/api/repo", tags=["repository"])


@router.post("/pull", response_class=JSONResponse)
async def pull_repo():
    command = ["git", "-C", DRY_PATH, "pull"]
    output = run_command(command, allow_failure=True)
    return {
        "status": "success" if not output.startswith("fatal:") else "error",
        "command": " ".join(command),
        "output": output,
    }


@router.get("/branches", response_class=JSONResponse)
async def list_branches():
    try:
        branches = get_git_branches(DRY_PATH)
        current_branch = get_current_git_branch(DRY_PATH)
        return {
            "status": "success",
            "branches": branches,
            "current": current_branch,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list branches: {e}")


@router.post("/checkout", response_class=JSONResponse)
async def checkout_branch(branch: str = Form(...)):
    command = ["git", "-C", DRY_PATH, "checkout", branch]
    output = run_command(command, allow_failure=True)
    return {
        "status": "success" if "error" not in output.lower() else "error",
        "command": " ".join(command),
        "output": output,
    }


def get_git_branches(repo_path: str) -> List[str]:
    command = ["git", "-C", repo_path, "branch", "-a", "--format=%(refname:short)"]
    output = run_command(command)
    raw_branches = output.strip().splitlines()

    branches = set()
    for branch in raw_branches:
        branch = branch.strip()
        if not branch or branch.endswith("HEAD"):
            continue
        if branch.startswith("remotes/"):
            branch = branch.replace("remotes/", "", 1)
        branches.add(branch)

    return sorted(branches)


def get_current_git_branch(repo_path: str) -> str:
    try:
        # Try to get the current symbolic branch
        return run_command(["git", "-C", repo_path, "symbolic-ref", "--short", "HEAD"])
    except HTTPException:
        pass  # Continue to fallback for detached HEAD

    try:
        # Detached HEAD: get short commit hash
        short_commit = run_command(
            ["git", "-C", repo_path, "rev-parse", "--short", "HEAD"]
        )

        remotes_output = run_command(
            ["git", "-C", repo_path, "branch", "-r", "--contains", short_commit],
            allow_failure=True,
        )
        remotes = [r.strip() for r in remotes_output.splitlines() if r.strip()]

        if remotes:
            return f"(HEAD detached at {remotes[0]})"
        else:
            return f"(HEAD detached at {short_commit})"
    except HTTPException:
        return "(unknown)"


@router.post("/fetch-status", response_class=JSONResponse)
async def fetch_status():
    try:
        # Fetch latest from remote
        run_command(["git", "-C", DRY_PATH, "fetch", "--prune"])

        detached = False

        # Try to get current branch name (symbolic ref)
        try:
            current_branch = run_command(
                ["git", "-C", DRY_PATH, "symbolic-ref", "--short", "HEAD"]
            )
        except HTTPException:
            # Detached HEAD — fallback to commit hash
            detached = True
            current_branch = run_command(
                ["git", "-C", DRY_PATH, "rev-parse", "--short", "HEAD"]
            )

        # Get local HEAD commit hash
        local_head = run_command(["git", "-C", DRY_PATH, "rev-parse", "HEAD"])

        # Try to determine matching remote branch
        remotes_output = run_command(
            ["git", "-C", DRY_PATH, "branch", "-r", "--contains", local_head],
            allow_failure=True,
        )

        remote_candidates = sorted(
            [
                r.strip()
                for r in remotes_output.splitlines()
                if r.strip() and "->" not in r
            ],
            key=lambda r: (not r.startswith("origin/"), r),
        )
        remote_branch = remote_candidates[0] if remote_candidates else None

        if not remote_branch:
            message = (
                f"Detached at commit {current_branch}, no matching remote tracking branch."
                if detached
                else f"{current_branch} is not tracking any remote branch."
            )
            remote_head = "(unknown)"
        else:
            remote_head = run_command(
                ["git", "-C", DRY_PATH, "rev-parse", remote_branch]
            )

            if remote_head == local_head:
                message = (
                    f"Detached HEAD is up to date with {remote_branch}."
                    if detached
                    else f"{current_branch} is up to date with {remote_branch}."
                )
            else:
                behind_count = run_command(
                    [
                        "git",
                        "-C",
                        DRY_PATH,
                        "rev-list",
                        "--count",
                        f"{local_head}..{remote_head}",
                    ],
                    allow_failure=True,
                )
                message = (
                    f"Detached HEAD is behind {remote_branch} by {behind_count} commits."
                    if detached
                    else f"{current_branch} is behind {remote_branch} by {behind_count} commits."
                )

        return {
            "status": "success",
            "branch": current_branch,
            "remote": remote_branch or "(unknown)",
            "local_head": local_head,
            "remote_head": remote_head,
            "message": message,
            "detached": detached,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fetch status failed: {e}")
