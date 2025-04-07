import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from app import routes
from app.routes import api as api_routes
from .middleware.auth import (
    add_auth_middleware,
    login_get,
    login_post,
    logout,
    admin_generate_auth_token,
)
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)
log.info("Starting up server now.")

app = FastAPI()

## Auth Routes:
add_auth_middleware(app)
app.add_api_route(
    "/login", login_get, methods=["GET"], response_class=HTMLResponse, tags=["auth"]
)
app.add_api_route(
    "/login", login_post, methods=["POST"], response_class=HTMLResponse, tags=["auth"]
)
app.add_api_route(
    "/logout", logout, methods=["GET"], response_class=HTMLResponse, tags=["auth"]
)
app.add_api_route(
    "/admin/generate-auth-token",
    admin_generate_auth_token,
    methods=["POST"],
    response_class=HTMLResponse,
    tags=["admin"],
)

# API Routes:
app.include_router(api_routes.ssh_config.router)
app.include_router(api_routes.docker_context.router)
app.include_router(api_routes.repo.router)
app.include_router(api_routes.terminal.router)
app.include_router(api_routes.env_dist.router)
app.include_router(api_routes.apps.router)

## Add static frontend route LAST:
public_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public"
)
app.mount(
    "/",
    StaticFiles(
        directory=public_path,
        html=True,
    ),
    name="static",
)
