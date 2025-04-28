import subprocess
from typing import List, Optional
from fastapi import HTTPException
import string
from typing import Dict, Tuple


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


def ensure_ends_with_punctuation(s: str) -> str:
    s = s.rstrip().rstrip(":")
    if s and s[-1] not in string.punctuation:
        return s + "."
    return s


def parse_env_file_contents(
    contents: str,
) -> Tuple[Dict[str, str], Dict[str, str], Dict[str, str]]:
    """
    Parses the contents of a .env file, returning:
    - env_dict: key-value pairs
    - env_comments: key-comment pairs (if any)
    - env_meta: parsed meta directives within '# META:' blocks
    """
    env_dict = {}
    env_comments = {}
    env_meta = {}
    comment_buffer = []

    lines = contents.splitlines()
    in_meta_block = False

    for line in lines:
        stripped = line.strip()

        # Handle blank lines
        if not stripped:
            comment_buffer = []
            in_meta_block = False
            continue

        # Detect start of meta block
        if stripped == "# META:":
            in_meta_block = True
            continue

        # If inside meta block, parse lines like '# KEY=VALUE'
        if in_meta_block and stripped.startswith("#"):
            content = stripped[1:].strip()
            if "=" in content:
                key, value = content.split("=", 1)
                env_meta[key.strip()] = value.strip()
                continue
            else:
                # malformed meta line or comment, stop meta block
                in_meta_block = False
                comment_buffer = []
                continue

        # If it's a comment but not part of meta
        if stripped.startswith("#"):
            comment_buffer.append(stripped.lstrip("# ").rstrip())
            continue

        # Parse regular key=value line
        if "=" in stripped:
            key, value = stripped.split("=", 1)
            key = key.strip()
            value = value.strip()
            env_dict[key] = value
            if comment_buffer:
                env_comments[key] = "\n".join(comment_buffer)
            comment_buffer = []
            in_meta_block = False  # end meta block if it was open

    return env_dict, env_comments, env_meta
