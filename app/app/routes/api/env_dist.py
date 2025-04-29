from app.routes import *
from .lib import (
    ensure_ends_with_punctuation,
    parse_env_file_contents,
    parse_makefile_open_hook_path,
)

router = APIRouter(prefix="/api/apps/env-dist", tags=["apps"])


async def get_env_dist_data(app: str) -> dict:
    env_path = os.path.join(DRY_PATH, app, ".env-dist")
    makefile_path = os.path.join(DRY_PATH, app, "Makefile")

    if not os.path.isfile(env_path):
        raise HTTPException(
            status_code=404, detail=f".env-dist file not found for app '{app}'"
        )

    if not os.path.isfile(makefile_path):
        raise HTTPException(
            status_code=404, detail=f"Makefile not found for app '{app}'"
        )

    try:
        with open(env_path, "r") as f:
            contents = f.read()
            env_dict, env_comments, env_meta = parse_env_file_contents(contents)
        with open(makefile_path, "r") as f:
            contents = f.read()
            http_path = parse_makefile_open_hook_path(contents)

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
                    "comments": ensure_ends_with_punctuation(env_comments.get(key, "")),
                }
                for key in env_dict
                if key not in env_meta  # optional: ignore meta vars from env
            },
            "meta": env_meta,
            "http_path": http_path,
        }

    except HTTPException:
        raise  # re-raise original HTTPException untouched
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def get_env_dist(app: str):
    data = await get_env_dist_data(app)
    return JSONResponse(data)
