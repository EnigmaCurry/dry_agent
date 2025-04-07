from app.routes import *
from app.routes import api as api_routes
import logging
import os
import re
import traceback
import subprocess
from fastapi import APIRouter, Request, HTTPException, Form
from fastapi.responses import JSONResponse

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/api/apps", tags=["apps"])


@router.get("/available", response_class=JSONResponse)
async def apps_available():
    command = [DRY_COMMAND, "list"]

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=True,
        )

        lines = result.stdout.strip().splitlines()
        service_lines = lines[1:]  # skip header
        apps = []
        for line in service_lines:
            apps.extend(line.strip().split())

        descriptions = parse_readme_descriptions()
        app_data = []

        for app in sorted(apps):
            try:
                # Only include if instantiable
                await api_routes.env_dist.get_env_dist_data(app)
                app_data.append(
                    {
                        "name": app,
                        "description": descriptions.get(
                            app, "No description available"
                        ),
                    }
                )
            except HTTPException as e:
                if e.status_code == 404:
                    continue  # skip non-instantiable
                else:
                    raise

        return JSONResponse(content={"apps": app_data})

    except Exception as e:
        logger.error("Failed to load available apps:\n%s", traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal Server Error: {str(e)}"},
        )


@router.get("/config", response_class=JSONResponse)
async def apps_config_data(app: str):
    try:
        data = await get_env_dist_data(app)
        env = data["env"]
        meta = data["meta"]

        instances = ["default"]  # Placeholder

        return JSONResponse(
            content={
                "app": app,
                "env": env,
                "meta": meta,
                "instances": instances,
                "contexts": ["default - TODO"],
            }
        )
    except Exception as e:
        logger.error("Failed to load config data:\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config", response_class=JSONResponse)
async def save_app_config(
    app: str = Form(...),
    context: str = Form(...),
    request: Request = None,
):
    form = await request.form()

    if not app or not context:
        raise HTTPException(status_code=400, detail="Missing 'app' or 'context'")

    data = await get_env_dist_data(app)
    prefix = data["meta"]["PREFIX"]

    instance_key = f"{prefix}_INSTANCE"
    instance = form.get(instance_key, "default").strip()

    env_filename = f".env_{context}_{instance}"
    env_path = os.path.join(DRY_PATH, app, env_filename)

    env_lines = []
    for key, value in form.items():
        if key.startswith("env_"):
            env_var = key[len("env_") :]
            env_lines.append(f"{env_var}={value}")
    env_lines.append(f"{instance_key}={instance}")

    try:
        with open(env_path, "w") as f:
            f.write("\n".join(env_lines) + "\n")

        return JSONResponse(
            content={
                "message": "Configuration saved",
                "env_file": env_filename,
                "app": app,
                "context": context,
                "instance": instance,
            },
            status_code=201,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write .env file: {e}")


def parse_readme_descriptions():
    readme_path = os.path.join(DRY_PATH, "README.md")

    if not os.path.exists(readme_path):
        return {}

    apps_with_descriptions = {}

    try:
        with open(readme_path, "r", encoding="utf-8") as file:
            lines = file.readlines()

        inside_section = False
        current_app = None
        expecting_description = False

        for line in lines:
            line = line.strip()

            if (
                "Install these first" in line
                or "Install these recommended backbone applications next:" in line
                or "Install these other services" in line
            ):
                inside_section = True
                continue

            if inside_section:
                match = re.match(
                    r"\*\s+\[(.*?)\]\((.*?)#readme\)\s*(?:-\s*(.*))?", line
                )

                if match:
                    display_name, link_name, description = match.groups()
                    link_name = link_name.strip().lower()

                    if description:
                        apps_with_descriptions[link_name] = description.strip()
                        current_app = None
                    else:
                        current_app = link_name
                        expecting_description = True
                    continue

                if current_app and expecting_description and line.startswith("*"):
                    apps_with_descriptions[current_app] = line.lstrip("*- ").strip()
                    current_app = None
                    expecting_description = False

    except Exception as e:
        print(f"Error reading README.md: {e}")

    return apps_with_descriptions
