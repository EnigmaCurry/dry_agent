# app/routes/terminal.py
import os
import pty
import asyncio
import select
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from app.dependencies import templates

router = APIRouter()


@router.get("/app/terminal", response_class=HTMLResponse)
async def terminal_page(request: Request):
    return templates.TemplateResponse("terminal.html", {"request": request})


@router.websocket("/ws/terminal")
async def terminal_ws(websocket: WebSocket):
    await websocket.accept()
    master_fd, slave_fd = pty.openpty()

    pid = os.fork()
    if pid == 0:
        os.setsid()
        os.dup2(slave_fd, 0)
        os.dup2(slave_fd, 1)
        os.dup2(slave_fd, 2)
        os.execv("/bin/bash", ["/bin/bash"])
    else:
        loop = asyncio.get_event_loop()

        async def read_pty():
            try:
                while True:
                    await asyncio.sleep(0.01)
                    if select.select([master_fd], [], [], 0)[0]:
                        data = os.read(master_fd, 1024).decode()
                        await websocket.send_text(data)
            except WebSocketDisconnect:
                pass

        asyncio.create_task(read_pty())

        try:
            while True:
                data = await websocket.receive_text()
                os.write(master_fd, data.encode())
        except WebSocketDisconnect:
            pass
