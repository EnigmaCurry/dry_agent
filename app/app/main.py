import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse
from app.dependencies import templates
from app.routes import repo, apps, env_dist, docker_context, terminal
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


# Routes:
app.include_router(repo.router)
app.include_router(apps.router)
app.include_router(env_dist.router)
app.include_router(docker_context.router)
app.include_router(terminal.router)
