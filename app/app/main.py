import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from app.dependencies import templates
from app import routes
from app.routes import api as api_routes
from .middleware.auth import (
    add_auth_middleware,
    login_get,
    login_post,
    logout,
    admin_generate_auth_token,
)

app = FastAPI()
add_auth_middleware(app)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.add_api_route("/login", login_get, methods=["GET"], response_class=HTMLResponse)
app.add_api_route("/login", login_post, methods=["POST"], response_class=HTMLResponse)
app.add_api_route("/logout", logout, methods=["GET"], response_class=HTMLResponse)
app.add_api_route(
    "/admin/generate-auth-token",
    admin_generate_auth_token,
    methods=["POST"],
    response_class=HTMLResponse,
)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# App Routes:
app.include_router(routes.repo.router)
app.include_router(routes.apps.router)
app.include_router(routes.env_dist.router)
app.include_router(routes.docker_context.router)
app.include_router(routes.terminal.router)

# API Routes:
app.include_router(api_routes.ssh_config.router)
app.include_router(api_routes.docker_context.router)
