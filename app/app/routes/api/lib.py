import subprocess
from typing import List, Optional
from fastapi import HTTPException


def run_command(cmd: List[str], timeout: Optional[int] = None) -> str:
    """
    Run a shell command and return its output.
    Optionally times out after the given number of seconds.
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
        raise HTTPException(
            status_code=500,
            detail=f"Command '{' '.join(cmd)}' failed: {e.stderr.strip()}",
        )
