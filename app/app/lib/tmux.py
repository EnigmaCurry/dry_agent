import os
import subprocess
from typing import Optional

TMUX_SESSION_DEFAULT = "work"


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


def inject_command_to_tmux(
    session_name: str,
    command: str,
    window_name: str = "injected",
    autorun: bool = False,
    active: bool = False,
):
    """
    Create a new tmux window in the given session, inject a command, and optionally run it or make it active.

    :param session_name: Name of the tmux session
    :param command: The shell command to pre-fill or run
    :param window_name: Optional name for the new window
    :param autorun: If True, presses Enter to run the command immediately
    :param active: If True, switch to the new window after creation
    """
    if not session_exists(session_name):
        subprocess.check_call(["tmux", "new-session", "-d", "-s", session_name])

    if window_exists(session_name, window_name):
        raise RuntimeError(
            f"Window '{window_name}' already exists in session '{session_name}'"
        )

    subprocess.check_call(["tmux", "new-window", "-t", session_name, "-n", window_name])

    target = f"{session_name}:{window_name}"

    subprocess.check_call(["tmux", "send-keys", "-t", target, command])

    if autorun:
        subprocess.check_call(["tmux", "send-keys", "-t", target, "Enter"])

    if active:
        subprocess.check_call(["tmux", "select-window", "-t", target])


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
