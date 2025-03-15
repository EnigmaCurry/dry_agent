from app.routes import *

router = APIRouter()

def parse_env_file_contents(contents: str) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Parses the contents of a .env file, returning:
    - env_dict: key-value pairs
    - env_comments: key-comment pairs (if any)
    """
    env_dict = {}
    env_comments = {}
    comment_buffer = []

    for line in contents.splitlines():
        stripped = line.strip()
        if not stripped:
            comment_buffer = []
            continue

        if stripped.startswith("#"):
            comment_buffer.append(stripped.lstrip("# "))
            continue

        if "=" in stripped:
            key, value = stripped.split("=", 1)
            key = key.strip()
            value = value.strip()
            env_dict[key] = value
            if comment_buffer:
                env_comments[key] = "\n".join(comment_buffer)
            comment_buffer = []

    return env_dict, env_comments

@router.get("/")
async def get_env_dist(service: str):
    env_path = os.path.join(DRY_PATH, service, ".env-dist")
    if not os.path.isfile(env_path):
        raise HTTPException(status_code=404, detail=f".env-dist file not found for service '{service}'")

    try:
        with open(env_path, "r") as f:
            contents = f.read()
            env_dict, env_comments = parse_env_file_contents(contents)
            combined_dict = {
                key: {
                    "default_value": env_dict[key],
                    "comments": env_comments.get(key, "")
                }
                for key in env_dict
            }
            return JSONResponse(combined_dict)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
