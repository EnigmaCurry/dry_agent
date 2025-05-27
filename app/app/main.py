import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from app import routes
from app.routes import api as api_routes
from .middleware.auth import (
    add_auth_middleware,
    login_get,
    login_post,
    logout,
    admin_generate_auth_token,
    get_login_url,
    admin_get_login_url,
)
import logging
from app.lib.docker_context_watcher import monitor_docker_context
from app.lib.tmux import start_tmux_socket_listener
from app.lib.xdg_open_pipe import watch_xdg_open_pipe
import asyncio
from app.lib.rate_limit import limiter, SlowAPIMiddleware, RateLimitExceeded

## Get TLS info from uvicorn:
import app.lib.patch_transport

LOG_LEVEL = os.getenv("LOG_LEVEL", "info").upper()
logging.basicConfig(level=LOG_LEVEL)
log = logging.getLogger(__name__)
log.info("Starting up server now.")

app = FastAPI()

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return PlainTextResponse("Rate limit exceeded", status_code=429)


## Auth Routes:
add_auth_middleware(app)
app.add_api_route(
    "/login", login_get, methods=["GET"], response_class=HTMLResponse, tags=["auth"]
)
app.add_api_route(
    "/login",
    login_post,
    methods=["POST"],
    response_class=HTMLResponse,
    tags=["auth"],
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
app.add_api_route(
    "/admin/get-login-url",
    admin_get_login_url,
    methods=["GET"],
    response_class=JSONResponse,
    tags=["app"],
)
app.add_api_route(
    "/get-login-url",
    get_login_url,
    methods=["GET"],
    response_class=JSONResponse,
    tags=["app"],
)

# API Routes:
app.include_router(api_routes.ssh_config.router)
app.include_router(api_routes.docker_context.router)
app.include_router(api_routes.repo.router)
app.include_router(api_routes.terminal.router)
app.include_router(api_routes.env_dist.router)
app.include_router(api_routes.projects.router)
app.include_router(api_routes.d_rymcg_tech.router)
app.include_router(api_routes.instances.router)
app.include_router(api_routes.chat.router)
app.include_router(api_routes.events.router)

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


@app.on_event("startup")
async def start_background_tasks():
    asyncio.create_task(monitor_docker_context())
    asyncio.create_task(watch_xdg_open_pipe())
    asyncio.create_task(start_tmux_socket_listener())
