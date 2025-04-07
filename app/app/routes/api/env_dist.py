from app.routes import *
from typing import Dict, Tuple

router = APIRouter(prefix="/api/apps/env-dist", tags=["apps"])


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


async def get_env_dist_data(app: str) -> dict:
    env_path = os.path.join(DRY_PATH, app, ".env-dist")
    if not os.path.isfile(env_path):
        raise HTTPException(
            status_code=404, detail=f".env-dist file not found for app '{app}'"
        )

    try:
        with open(env_path, "r") as f:
            contents = f.read()
            env_dict, env_comments, env_meta = parse_env_file_contents(contents)

            # Ensure 'PREFIX' is always present in meta
            env_meta = dict(env_meta)  # Ensure it's mutable
            env_meta.setdefault("PREFIX", app.replace("-", "_").upper())

            # If INSTANTIABLE is anything but "true", abort early
            if env_meta.get("INSTANTIABLE", "true").strip().lower() != "true":
                raise HTTPException(
                    status_code=404, detail=f"App '{app}' is not instantiable"
                )

            # Remove INSTANTIABLE from the results
            env_meta.pop("INSTANTIABLE", None)

            return {
                "env": {
                    key: {
                        "default_value": env_dict[key],
                        "comments": env_comments.get(key, ""),
                    }
                    for key in env_dict
                    if key not in env_meta  # optional: ignore meta vars from env
                },
                "meta": env_meta,
            }

    except HTTPException:
        raise  # re-raise original HTTPException untouched
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def get_env_dist(app: str):
    data = await get_env_dist_data(app)
    return JSONResponse(data)
