# app/routes/terminal.py
import os
import pty
import asyncio
import select
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from app.dependencies import templates
import fcntl
import termios
import struct
import json
import signal
import prctl
import errno

router = APIRouter()


@router.get("/app/terminal", response_class=HTMLResponse)
async def terminal_page(request: Request):
    return templates.TemplateResponse("terminal.html", {"request": request})


@router.websocket("/app/terminal/ws")
async def terminal_ws(websocket: WebSocket):
    await websocket.accept()

    master_fd, slave_fd = pty.openpty()
    pid = os.fork()

    if pid == 0:
        os.setsid()
        prctl.set_pdeathsig(signal.SIGTERM)
        os.dup2(slave_fd, 0)
        os.dup2(slave_fd, 1)
        os.dup2(slave_fd, 2)
        os.close(slave_fd)

        # Optional: clean environment
        env = {
            "TERM": "xterm-256color",
            "PATH": "/usr/bin:/bin",
            "HOME": os.environ.get("HOME", "/tmp"),
        }

        os.execve("/bin/bash", ["/bin/bash"], env)

    else:
        reaper_task = asyncio.create_task(reap_children())

        def set_pty_size(fd, cols, rows):
            size = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(fd, termios.TIOCSWINSZ, size)

        async def wait_for_exit():
            _, _ = await asyncio.to_thread(os.waitpid, pid, 0)
            await websocket.send_text("__exit__")
            await websocket.close()

        wait_task = asyncio.create_task(wait_for_exit())

        async def read_pty():
            try:
                while True:
                    await asyncio.sleep(0.01)
                    if select.select([master_fd], [], [], 0)[0]:
                        data = os.read(master_fd, 1024).decode()
                        await websocket.send_text(data)
            except Exception:
                pass

        pty_task = asyncio.create_task(read_pty())

        try:
            while True:
                msg = await websocket.receive_text()
                try:
                    parsed = json.loads(msg)
                    if parsed.get("type") == "resize":
                        set_pty_size(master_fd, parsed["cols"], parsed["rows"])
                    else:
                        raise JSONDecodeError("Unhandled json", msg, 0)
                except (AttributeError, json.JSONDecodeError):
                    os.write(master_fd, msg.encode())

        except WebSocketDisconnect:
            print("🔌 WebSocket disconnected. Cleaning up...")
            try:
                os.killpg(pid, signal.SIGTERM)  # try to terminate the shell nicely
                await asyncio.sleep(0.1)  # give it a moment to shut down
                os.killpg(pid, signal.SIGKILL)  # force kill if still alive
            except ProcessLookupError:
                pass  # already exited

            try:
                os.close(master_fd)
            except OSError:
                pass
            try:
                pty_task.cancel()
            except Exception:
                pass

            try:
                wait_task.cancel()
            except Exception:
                pass
            await asyncio.gather(pty_task, wait_task, return_exceptions=True)
            reaper_task.cancel()
            await asyncio.gather(reaper_task, return_exceptions=True)


async def reap_children():
    while True:
        try:
            # Wait for ANY child process (bash or its children)
            pid, _ = await asyncio.to_thread(os.waitpid, -1, os.WNOHANG)
            if pid == 0:
                await asyncio.sleep(0.1)
            else:
                print(f"🧼 Reaped zombie child: PID {pid}")
        except ChildProcessError:
            break  # no more children
        except OSError as e:
            if e.errno == errno.ECHILD:
                break  # no child processes remain
            raise
