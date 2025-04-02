import subprocess
from typing import List, Optional
from fastapi import HTTPException


def run_command(
    cmd: List[str], timeout: Optional[int] = None, allow_failure: bool = False
) -> str:
    """
    Run a shell command and return its output.
    Optionally times out after the given number of seconds.

    If allow_failure is False (default), a command failure raises a 500 error.
    If allow_failure is True, a failure returns the command's output (stdout if available, otherwise stderr)
    instead of raising an exception.
    """
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=504,
            detail=f"Command '{' '.join(cmd)}' timed out after {timeout} seconds.",
        )
    except subprocess.CalledProcessError as e:
        if allow_failure:
            # Return stdout if available, otherwise return stderr.
            return e.stdout.strip() or e.stderr.strip()
        raise HTTPException(
            status_code=500,
            detail=f"Command '{' '.join(cmd)}' failed: {e.stderr.strip()}",
        )
