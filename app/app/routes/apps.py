from app.routes import *
from app.dependencies import templates
from app.routes.env_dist import get_env_dist_data
import traceback
import logging

logger = logging.getLogger("uvicorn.error")

router = APIRouter()

@router.get("/app/apps/available", response_class=HTMLResponse)
async def apps_page(request: Request):
    return templates.TemplateResponse("apps_available.html", {
        "request": request,
    })

@router.get("/api/apps/available", response_class=HTMLResponse)
async def apps_available(request: Request):
    command = [DRY_COMMAND, "list"]

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=True
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
                await get_env_dist_data(app)
                app_data.append({
                    "name": app,
                    "description": descriptions.get(app, "No description available")
                })
            except HTTPException as e:
                if e.status_code == 404:
                    continue  # skip non-instantiable
                else:
                    raise

        return templates.TemplateResponse("partials/apps_list.html", {
            "request": request,
            "apps": app_data,
        })

    except Exception as e:
        logger.error("Failed to load available apps:\n%s", traceback.format_exc())

        return HTMLResponse(
            content=f"<p class='has-text-danger'>❌ Internal Server Error:<br><pre>{e}</pre></p>",
            status_code=500
        )

@router.get("/app/apps/config", response_class=HTMLResponse)
async def apps_config_page(request: Request, app: str):
    data = await get_env_dist_data(app)
    env = data['env']
    meta = data['meta']

    # You can fetch real instances from disk or database
    instances = ["default"]  # Placeholder

    return templates.TemplateResponse("apps_config.html", {
        "request": request,
        "app": app,
        "env": env,
        "meta": meta,
        "instances": instances,
    })

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
        expecting_description = False  # Flag to check if we need to grab the next line

        for line in lines:
            line = line.strip()

            # Detect the start of the "Install" section
            if "Install these first" in line or "Install these recommended backbone applications next:" in line or "Install these other services" in line:
                inside_section = True
                continue

            if inside_section:
                # Match "* [AppName](link#readme) - Description"
                match = re.match(r"\*\s+\[(.*?)\]\((.*?)#readme\)\s*(?:-\s*(.*))?", line)

                if match:
                    display_name, link_name, description = match.groups()
                    link_name = link_name.strip().lower()  # Normalize for matching

                    if description:
                        apps_with_descriptions[link_name] = description.strip()
                        current_app = None  # Reset
                    else:
                        # ✅ If no description, flag to capture the next line
                        current_app = link_name
                        expecting_description = True
                    continue  # Move to the next line

                # ✅ If the last app was missing a description, check this line
                if current_app and expecting_description and line.startswith("*"):
                    apps_with_descriptions[current_app] = line.lstrip("*- ").strip()
                    current_app = None
                    expecting_description = False

        #print("Extracted Descriptions:", apps_with_descriptions)

    except Exception as e:
        print(f"Error reading README.md: {e}")

    return apps_with_descriptions
