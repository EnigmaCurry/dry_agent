import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse
from app.dependencies import templates
from app.routes import repo, apps, env_dist

app = FastAPI()

app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/favicon.ico")
async def favicon():
    return FileResponse("app/static/favicon.ico")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", { "request": request })

# Routes:
app.include_router(repo.router)
app.include_router(apps.router)
app.include_router(env_dist.router)
