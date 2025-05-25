# app/routes/terminal.py
import os
import pty
import asyncio
import select
from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
    HTTPException,
    Query,
    Path,
)
from fastapi.responses import JSONResponse
import fcntl
import termios
import struct
import json
import signal
import errno
import logging
import subprocess
from typing import Optional
from app.lib.tmux import (
    get_tmux_pane_cwd_path,
    inject_command_to_tmux,
    get_windows,
    set_window_active,
    create_new_window,
    TMUX_SESSION_DEFAULT,
)
from app.broadcast import broadcast, subscribe, unsubscribe
from app.models.events import OpenAppEvent, Event, LogoutEvent, TmuxSessionChangedEvent

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/terminal", tags=["terminal"])


async def watch_for_logout(queue: asyncio.Queue, websocket: WebSocket):
    try:
        while True:
            event = await queue.get()
            if isinstance(event, LogoutEvent):
                log.info("LogoutEvent received, closing terminal websocket.")
                await websocket.close(code=4001)  # Use custom close code
                break
    except Exception as e:
        log.warning(f"watch_for_logout error: {e}")


@router.websocket("/ws")
async def terminal_ws(websocket: WebSocket):
    await websocket.accept()
    event_queue = await subscribe()
    logout_watcher = asyncio.create_task(watch_for_logout(event_queue, websocket))

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

        pty_done = asyncio.Event()

        async def wait_for_exit():
            try:
                _, status = await asyncio.to_thread(os.waitpid, pid, 0)
                exit_code = os.WEXITSTATUS(status)
                log.info(f"Terminal command exited with code: {exit_code}")

                try:
                    os.close(slave_fd)  # Close the slave side after the child exits
                except Exception:
                    pass

                # Wait for PTY reader to finish draining
                await pty_done.wait()

                try:
                    await websocket.send_text(
                        json.dumps({"type": "exit", "exitCode": exit_code})
                    )
                except Exception:
                    pass

                await websocket.close()
            except Exception as ex:
                print(f"Error waiting for process exit: {ex}")

        wait_task = asyncio.create_task(wait_for_exit())

        async def read_pty():
            try:
                while True:
                    await asyncio.sleep(0.01)
                    if select.select([master_fd], [], [], 0)[0]:
                        try:
                            data = os.read(master_fd, 1024)
                            if not data:
                                break  # PTY closed (EOF)
                            await websocket.send_text(
                                json.dumps(
                                    {
                                        "type": "data",
                                        "data": data.decode(errors="ignore"),
                                    }
                                )
                            )
                        except OSError:
                            break
            except Exception as ex:
                print(f"Error reading from PTY: {ex}")
            finally:
                pty_done.set()

        pty_task = asyncio.create_task(read_pty())

        # ─── start a background task to watch /proc/<pane-pid>/cwd ───
        async def watch_cwd():
            last = None
            # on connect, immediately try to send the current cwd
            path_link = get_tmux_pane_cwd_path(TMUX_SESSION_DEFAULT)
            if path_link:
                try:
                    dest = os.readlink(path_link)
                    last = dest
                    await websocket.send_text(json.dumps({"type": "cwd", "path": dest}))
                except Exception:
                    pass
            # then poll once a second, sending only on change
            while True:
                await asyncio.sleep(1)
                path_link = get_tmux_pane_cwd_path(TMUX_SESSION_DEFAULT)
                if not path_link:
                    continue
                try:
                    dest = os.readlink(path_link)
                except Exception:
                    continue
                if dest != last:
                    last = dest
                    try:
                        await websocket.send_text(
                            json.dumps({"type": "cwd", "path": dest})
                        )
                    except Exception:
                        break

        cwd_task = asyncio.create_task(watch_cwd())

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
            logout_watcher.cancel()
            await asyncio.gather(logout_watcher, return_exceptions=True)
            unsubscribe(event_queue)
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
            cwd_task.cancel()
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


@router.post("/{session_name}/window")
async def create_tmux_window(
    session_name: str = Path(...),
    window_name: Optional[str] = Query("new"),
    active: bool = Query(False),
):
    try:
        create_new_window(
            session_name=session_name,
            window_name=window_name,
            active=active,
        )
        if active:
            await broadcast(OpenAppEvent(page="workstation"))
        await broadcast(
            TmuxSessionChangedEvent(session=session_name, **get_windows(session_name))
        )
        return JSONResponse(
            content={
                "status": "ok",
                "message": f"Window '{window_name}' created and command injected",
            }
        )
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"tmux error: {e}")


@router.get("/{session_name}/window")
async def get_tmux_windows(session_name: str = Path(...)):
    try:
        return {"session": session_name, **get_windows(session_name)}
    except RuntimeError:
        return {"session": session_name, "windows": [], "active": None}


@router.put("/{session_name}/window/active")
async def set_active_window(
    session_name: str = Path(...),
    index: int = Query(..., description="Index of the window to activate"),
):
    success = set_window_active(session_name, index)
    if not success:
        raise HTTPException(status_code=404, detail="Session or window not found")

    # Emit updated state after switching
    state = get_windows(session_name)
    await broadcast(TmuxSessionChangedEvent(session=session_name, **state))

    return {"session": session_name, "active": state["active"]}
