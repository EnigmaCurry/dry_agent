# app/routes/terminal.py
import os
import sys
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
import errno
import logging

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/terminal", tags=["terminal"])


@router.websocket("/ws")
async def terminal_ws(websocket: WebSocket):
    await websocket.accept()

    initial_command_received = False
    try:
        while not initial_command_received:
            msg = await websocket.receive_text()
            try:
                init_data = json.loads(msg)
            except json.JSONDecodeError:
                continue  # Ignore malformed JSON until we get the command.

            if "command" in init_data:
                command = init_data["command"]
                initial_command_received = True
                log.info(f"Teminal command request received: {command}")
            else:
                continue
    except WebSocketDisconnect:
        return
    except Exception as e:
        print(f"Error waiting for initial command: {e}")
        return

    master_fd, slave_fd = pty.openpty()
    pid = os.fork()

    if pid == 0:
        os.setsid()
        os.dup2(slave_fd, 0)
        os.dup2(slave_fd, 1)
        os.dup2(slave_fd, 2)
        os.close(slave_fd)
        env = {
            "TERM": "xterm-256color",
            "PATH": "/usr/bin:/bin",
            "HOME": os.environ.get("HOME", "/tmp"),
        }
        os.execvpe("/bin/bash", ["bash", "-i", "-c", command], env)
    else:
        if not hasattr(terminal_ws, "_reaper_started"):
            terminal_ws._reaper_started = True
            asyncio.create_task(reap_children())

        async def wait_for_exit():
            try:
                _, _ = await asyncio.to_thread(os.waitpid, pid, 0)
            except Exception as ex:
                print(f"Error waiting for process exit: {ex}")
            try:
                await websocket.send_text(json.dumps({"type": "exit"}))
            except Exception:
                pass
            await websocket.close()

        wait_task = asyncio.create_task(wait_for_exit())

        async def read_pty():
            try:
                while True:
                    await asyncio.sleep(0.01)
                    if select.select([master_fd], [], [], 0)[0]:
                        data = os.read(master_fd, 1024).decode(errors="ignore")
                        # Wrap terminal data in a JSON message.
                        try:
                            await websocket.send_text(
                                json.dumps({"type": "data", "data": data})
                            )
                        except Exception:
                            break
            except Exception as ex:
                print(f"Error reading from PTY: {ex}")

        pty_task = asyncio.create_task(read_pty())

        try:
            while True:
                msg = await websocket.receive_text()
                try:
                    parsed = json.loads(msg)
                    msg_type = parsed.get("type")
                    if msg_type == "resize":
                        cols = parsed.get("cols")
                        rows = parsed.get("rows")
                        size = struct.pack("HHHH", rows, cols, 0, 0)
                        fcntl.ioctl(master_fd, termios.TIOCSWINSZ, size)
                    elif msg_type == "input":
                        # User input sent from client.
                        user_input = parsed.get("data", "")
                        os.write(master_fd, user_input.encode())
                    else:
                        # If an unrecognized JSON message is received, ignore or handle appropriately.
                        pass
                except (json.JSONDecodeError, AttributeError):
                    # In case a non-JSON message slips through.
                    os.write(master_fd, msg.encode())
        except WebSocketDisconnect:
            print("WebSocket disconnected. Cleaning up...")
        except Exception as e:
            print(f"Unexpected error: {e}")
        finally:
            try:
                os.killpg(pid, signal.SIGTERM)
                await asyncio.sleep(0.1)
                os.killpg(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                os.close(master_fd)
            except OSError:
                pass
            pty_task.cancel()
            wait_task.cancel()
            await asyncio.gather(pty_task, wait_task, return_exceptions=True)


async def reap_children():
    while True:
        try:
            pid, _ = await asyncio.to_thread(os.waitpid, -1, os.WNOHANG)
            if pid == 0:
                await asyncio.sleep(0.1)
            else:
                print(f"🧼 Reaped zombie child: PID {pid}")
        except ChildProcessError:
            # No children to wait for *right now*, just wait and try again later
            await asyncio.sleep(0.5)
        except OSError as e:
            if e.errno == errno.ECHILD:
                await asyncio.sleep(0.5)
            else:
                raise
