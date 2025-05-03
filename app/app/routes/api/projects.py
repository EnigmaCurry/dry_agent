from app.routes import DRY_COMMAND, DRY_PATH
from app.routes import api as api_routes
import logging
import os
import re
import traceback
import subprocess
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from .lib import parse_docker_compose_services

"""
General information about available projects and default configs.
"""

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/api/projects", tags=["projects"])

from fastapi.responses import JSONResponse
from fastapi import HTTPException
import subprocess
import traceback
import logging

logger = logging.getLogger("uvicorn.error")


async def get_available_projects():
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
        projects = []
        for line in service_lines:
            projects.extend(line.strip().split())

        descriptions = parse_readme_descriptions()
        app_data = []

        for app in sorted(projects):
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

        return app_data

    except Exception:
        logger.error("Failed to load available projects:\n%s", traceback.format_exc())
        raise


@router.get("/available/")
async def get_projects_available():
    try:
        app_data = await get_available_projects()
        return JSONResponse(content={"projects": app_data})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal Server Error: {str(e)}"},
        )


@router.get("/services/", response_class=JSONResponse)
async def get_app_services(app: str = Query()):
    docker_compose_path = os.path.join(DRY_PATH, app, "docker-compose.yaml")
    if not os.path.isfile(docker_compose_path):
        return JSONResponse(
            status_code=404,
            content={"detail": f"Could not find docker-compose.yaml for app: {app}"},
        )
    with open(docker_compose_path) as f:
        docker_compose_content = f.read()
    try:
        services = parse_docker_compose_services(docker_compose_content)
    except ValueError:
        return JSONResponse(
            status_code=500,
            content={"detail": f"Could not parse: {docker_compose_path}"},
        )
    return {"app": app, "services": services}


def parse_readme_descriptions():
    readme_path = os.path.join(DRY_PATH, "README.md")

    if not os.path.exists(readme_path):
        return {}

    projects_with_descriptions = {}

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
                        projects_with_descriptions[link_name] = description.strip()
                        current_app = None
                    else:
                        current_app = link_name
                        expecting_description = True
                    continue

                if current_app and expecting_description and line.startswith("*"):
                    projects_with_descriptions[current_app] = line.lstrip("*- ").strip()
                    current_app = None
                    expecting_description = False

    except Exception as e:
        print(f"Error reading README.md: {e}")

    return projects_with_descriptions
