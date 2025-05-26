import os
import subprocess
from typing import Optional, TypedDict, Union
import re
from pathlib import Path
import socket
import asyncio
from app.models.events import TmuxSessionChangedEvent
from app.broadcast import broadcast

TMUX_SESSION_DEFAULT = "work"

# Socket that shows tmux session state changes from tmux hooks
SOCKET_PATH = "/run/tmux-event.sock"


def window_exists(session_name: str, window_name: str) -> bool:
    try:
        output = subprocess.check_output(
            ["tmux", "list-windows", "-t", session_name],
            stderr=subprocess.DEVNULL,
        ).decode()
        return any(
            f"{window_name}" in line.split(":")[1].strip()
            for line in output.splitlines()
        )
    except subprocess.CalledProcessError:
        return False


def session_exists(session_name: str) -> bool:
    try:
        subprocess.check_output(
            ["tmux", "has-session", "-t", session_name],
            stderr=subprocess.DEVNULL,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def create_new_window(
    session_name: str,
    window_name: str = "injected",
    active: bool = False,
) -> int:
    """
    Create a new tmux window in the given session and return its index.

    :param session_name: Name of the tmux session
    :param window_name: Optional name for the new window
    :param active: If True, switch to the new window after creation
    :return: The index of the newly created window
    """
    if not session_exists(session_name):
        subprocess.check_call(["tmux", "new-session", "-d", "-s", session_name])

    # Get current window indexes
    output = subprocess.check_output(
        ["tmux", "list-windows", "-t", session_name, "-F", "#{window_index}"],
        stderr=subprocess.DEVNULL,
    ).decode()

    existing_indexes = sorted(
        int(line.strip())
        for line in output.strip().splitlines()
        if line.strip().isdigit()
    )
    new_index = (existing_indexes[-1] + 1) if existing_indexes else 0

    # Create the new window
    subprocess.check_call(["tmux", "new-window", "-t", session_name, "-n", window_name])

    if active:
        subprocess.check_call(
            ["tmux", "select-window", "-t", f"{session_name}:{new_index}"]
        )

    return new_index


def inject_command_to_tmux(
    session_name: str,
    command: str,
    window_name: str = "injected",
    autorun: bool = False,
    active: bool = False,
):
    """
    Create a new tmux window in the given session, inject a command, and optionally run it or make it active.
    """
    new_index = create_new_window(session_name, window_name=window_name, active=active)
    target = f"{session_name}:{new_index}"

    subprocess.check_call(["tmux", "send-keys", "-t", target, command])
    if autorun:
        subprocess.check_call(["tmux", "send-keys", "-t", target, "Enter"])


def get_tmux_pane_cwd_path(session: str) -> Optional[str]:
    def get_latest_child_pid(pid: str) -> str:
        """Recursively find the most recent child/grandchild process."""
        try:
            with open(f"/proc/{pid}/task/{pid}/children", "r") as f:
                children = f.read().strip().split()
                if not children:
                    return pid
                # Pick the last child PID as the most recent one
                return get_latest_child_pid(children[-1])
        except Exception:
            return pid

    try:
        # 1. Get the pane ID
        pane_id = (
            subprocess.check_output(
                ["tmux", "display-message", "-p", "-t", session, "#{pane_id}"],
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )
        if not pane_id:
            return None

        # 2. Get pane PID
        lines = (
            subprocess.check_output(
                ["tmux", "list-panes", "-t", session, "-F", "#{pane_id} #{pane_pid}"],
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .splitlines()
        )

        for tid, pid in (line.split() for line in lines):
            if tid == pane_id:
                # 3. Find the latest descendant PID
                active_pid = get_latest_child_pid(pid)
                path = f"/proc/{active_pid}/cwd"
                if os.path.exists(path):
                    return path

    except subprocess.CalledProcessError:
        pass

    return None


def get_windows(session_name: str) -> dict[str, Union[list[dict], int]]:
    """
    Return a dictionary with all window names and indexes,
    and the index of the currently active window.

    :param session_name: The name of the tmux session
    :return: Dict with keys: 'windows' (list of dicts with name/index), 'active' (index)
    """
    if not session_exists(session_name):
        raise RuntimeError(f"Session '{session_name}' does not exist")

    try:
        output = subprocess.check_output(
            ["tmux", "list-windows", "-t", session_name],
            stderr=subprocess.DEVNULL,
        ).decode()
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"Failed to list windows for session '{session_name}'"
        ) from e

    windows = []
    active_index = None

    for line in output.strip().splitlines():
        parts = line.split(":", 1)
        if len(parts) < 2:
            continue

        try:
            index = int(parts[0])
        except ValueError:
            continue

        name_with_flags = parts[1].strip().split(" ", 1)[0]
        name = re.sub(r"[\*\-\+\~\@\!]+$", "", name_with_flags)

        windows.append(
            {
                "index": index,
                "name": name,
            }
        )

        if name_with_flags.endswith("*"):
            active_index = index

    return {
        "windows": windows,
        "active": active_index,
    }


async def start_tmux_socket_listener():
    # Clean up old socket if needed
    sock_path = Path(SOCKET_PATH)
    if sock_path.exists():
        sock_path.unlink()

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(SOCKET_PATH)
    server.listen()

    print(f"[tmux] Listening for tmux events on {SOCKET_PATH}")

    loop = asyncio.get_running_loop()

    while True:
        conn, _ = await loop.sock_accept(server)
        data = await loop.sock_recv(conn, 1024)
        print(f"[tmux] socket yielded data: {data}")
        session_name = data.decode().strip()
        conn.close()

        try:
            state = get_windows(session_name)
            event = TmuxSessionChangedEvent(session=session_name, **state)
            await broadcast(event)
        except Exception as e:
            print(f"[tmux] Failed to broadcast update: {e}")


def set_window_active(session_name: str, window_index: int) -> bool:
    """
    Makes the window at the given index active in the tmux session.

    :param session_name: Name of the tmux session
    :param window_index: Index of the window to activate
    :return: True if successful, False otherwise
    """
    if not session_exists(session_name):
        return False

    try:
        subprocess.check_call(
            ["tmux", "select-window", "-t", f"{session_name}:{window_index}"],
            stderr=subprocess.DEVNULL,
        )
        return True
    except subprocess.CalledProcessError:
        raise RuntimeError(
            f"Could not activate window {window_index} in session: {session_name}"
        )


def delete_window(session_name: str, window_index: int) -> bool:
    """
    Deletes the specified tmux window by killing the window.

    :param session_name: Name of the tmux session
    :param window_index: Index of the tmux window to delete
    :return: True if successful, False otherwise
    """
    try:
        subprocess.check_call(
            ["tmux", "kill-window", "-t", f"{session_name}:{window_index}"]
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to delete tmux window: {e}")
        return False
