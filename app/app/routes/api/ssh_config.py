import os
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from .lib import run_command
import logging

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ssh_config", tags=["ssh_config"])


class SSHConfigEntry(BaseModel):
    Host: str
    Hostname: str
    User: str
    Port: int


def parse_ssh_config(config_path):
    """
    Parse an SSH config file into a list of dictionaries.
    Each dictionary corresponds to a "Host" entry with its settings.
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"{config_path} does not exist.")

    hosts = []
    current_host = None

    with open(config_path, "r") as f:
        for line in f:
            line = line.strip()
            # Skip blank lines and comments
            if not line or line.startswith("#"):
                continue

            # New host block
            if line.lower().startswith("host "):
                # If there's an active host, store it first.
                if current_host is not None:
                    hosts.append(current_host)
                # Create a new host entry
                host_patterns = line.split()[1:]
                current_host = {"Host": host_patterns}
            elif current_host is not None:
                # Split line into key-value pair. Allow '=' as well.
                if "=" in line:
                    key, value = map(str.strip, line.split("=", 1))
                else:
                    parts = line.split(maxsplit=1)
                    key = parts[0]
                    value = parts[1] if len(parts) > 1 else ""
                    if key.lower() == "port":
                        try:
                            value = int(value)
                        except ValueError:
                            pass
                # Store configuration parameter
                current_host[key] = value

    # Append the last host entry if exists.
    if current_host is not None:
        hosts.append(current_host)

    return hosts


@router.get("/", response_class=JSONResponse)
async def ssh_config(request: Request):
    try:
        home = os.environ.get("HOME")
        if not home:
            raise EnvironmentError("HOME environment variable not set.")
        config_path = os.path.join(home, ".ssh", "config")
        parsed_config = parse_ssh_config(config_path)
        return JSONResponse(content=parsed_config)
    except Exception as e:
        log.error(e)
        raise HTTPException(status_code=500, detail=str(e))


def remove_ssh_config_entry(ssh_config_path: str, host_alias: str) -> bool:
    """Remove the SSH config block for a given host alias.

    Returns:
        True if a block was removed, False otherwise.
    """
    removed = False
    try:
        with open(ssh_config_path, "r") as f:
            lines = f.readlines()
    except Exception as e:
        raise Exception(f"Error reading SSH config: {e}")

    new_lines = []
    skip = False

    for line in lines:
        # If we hit a new host block, check if it should be removed.
        if line.strip().startswith("Host "):
            host_patterns = line.strip().split()[1:]
            if host_alias in host_patterns:
                # Set flag to skip this block.
                skip = True
                removed = True
                continue
            else:
                # Starting a new block so stop skipping.
                skip = False
        if not skip:
            new_lines.append(line)

    try:
        with open(ssh_config_path, "w") as f:
            f.writelines(new_lines)
    except Exception as e:
        raise Exception(f"Error writing SSH config: {e}")

    return removed


@router.delete("/{host_alias}", response_class=JSONResponse)
async def delete_ssh_config_entry(host_alias: str, request: Request):
    try:
        home = os.environ.get("HOME")
        if not home:
            raise EnvironmentError("HOME environment variable not set.")
        ssh_config_path = os.path.join(home, ".ssh", "config")
        if not os.path.exists(ssh_config_path):
            raise FileNotFoundError("SSH config file does not exist.")

        # Attempt to remove the entry.
        removed = remove_ssh_config_entry(ssh_config_path, host_alias)
        if not removed:
            raise HTTPException(
                status_code=404,
                detail=f"No SSH config entry found for host '{host_alias}'.",
            )

        return JSONResponse(
            content={"detail": f"SSH config entry for host '{host_alias}' removed."}
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def upsert_ssh_config_entry(ssh_config_path: str, entry: SSHConfigEntry):
    """
    Remove an existing entry for the given host alias (if any)
    and append a new entry to the SSH config file.
    """
    # Remove any existing block for this host alias.
    remove_ssh_config_entry(ssh_config_path, entry.Host)

    # Append the new entry to the file.
    with open(ssh_config_path, "a") as f:
        # Ensure a newline between blocks.
        f.write("\n")
        f.write(f"Host {entry.Host}\n")
        f.write(f"    HostName {entry.Hostname}\n")
        f.write(f"    User {entry.User}\n")
        f.write(f"    Port {entry.Port}\n")


@router.post("/", response_class=JSONResponse)
async def create_or_update_ssh_config_entry(entry: SSHConfigEntry, request: Request):
    try:
        home = os.environ.get("HOME")
        if not home:
            raise EnvironmentError("HOME environment variable not set.")

        ssh_config_path = os.path.join(home, ".ssh", "config")

        # Create the .ssh directory if it doesn't exist.
        ssh_dir = os.path.join(home, ".ssh")
        if not os.path.exists(ssh_dir):
            os.makedirs(ssh_dir, mode=0o700)

        # If the config file doesn't exist, create it.
        if not os.path.exists(ssh_config_path):
            open(ssh_config_path, "a").close()

        # Upsert the SSH config entry.
        upsert_ssh_config_entry(ssh_config_path, entry)

        return JSONResponse(
            content={
                "detail": f"SSH config entry for host '{entry.Host}' created/updated."
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def test_ssh_connection(host: str) -> str:
    """
    Test SSH connection to the given host alias by verifying that the output of
    "ssh {host} whoami" matches the configured username in the SSH config file.

    Raises:
        Exception: If the HOME environment variable is not set.
        Exception: If the SSH config file doesn't exist or the host config is missing.
        Exception: If the configured username is not set.
        Exception: If the SSH connection output does not match the configured username.

    Returns:
        str: The username returned from the SSH connection command.
    """
    home = os.environ.get("HOME")
    if not home:
        raise Exception("HOME environment variable not set.")
    config_path = os.path.join(home, ".ssh", "config")

    # Parse the SSH config file
    config_entries = parse_ssh_config(config_path)

    # Find the SSH config entry matching the given host alias.
    found_entry = None
    for entry in config_entries:
        host_patterns = entry.get("Host")
        if host_patterns and isinstance(host_patterns, list):
            if host in host_patterns:
                found_entry = entry
                break
        elif host_patterns == host:
            found_entry = entry
            break

    if not found_entry:
        raise Exception(f"No SSH config entry found for host '{host}'.")

    expected_user = found_entry.get("User")
    if not expected_user:
        raise Exception(f"SSH config for host '{host}' does not specify a username.")

    # Execute the SSH command to test the connection.
    output = run_command(
        [
            "ssh",
            "-o",
            "StrictHostKeyChecking=accept-new",
            host,
            "whoami",
        ],
        timeout=5,
    )

    # Clean the output to remove extra whitespace/newlines.
    actual_user = output.strip()

    if actual_user != expected_user.strip():
        raise Exception(
            f"SSH connection test failed: expected username '{expected_user}', got '{actual_user}'."
        )

    return actual_user


@router.get("/test/{host_alias}", response_class=JSONResponse)
async def test_ssh_connection_route(host_alias: str, request: Request):
    """
    FastAPI route to test an SSH connection for a given host alias.
    It verifies that the 'whoami' command output matches the configured username.
    """
    try:
        username = test_ssh_connection(host_alias)
        return JSONResponse(
            content={
                "detail": f"SSH connection test successful for host '{host_alias}'.",
                "username": username,
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/key", response_class=JSONResponse)
async def ssh_key(request: Request):
    "Get the dry_agent client ssh key"
    key_path = os.path.expanduser("~/.ssh/id_ed25519.pub")
    if not os.path.isfile(key_path):
        raise HTTPException(status_code=404, detail="SSH public key not found")
    try:
        with open(key_path, "r") as f:
            key = f.read().strip()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail="Error reading SSH public key"
        ) from e

    return {"key": key}


def get_trusted_fingerprint(host_alias: str) -> str:
    """
    Looks up the SSH alias in the config and retrieves the fingerprint
    using the actual HostName.
    """
    home = os.environ.get("HOME")
    if not home:
        raise HTTPException(
            status_code=500, detail="HOME environment variable not set."
        )

    config_path = os.path.join(home, ".ssh", "config")
    known_hosts_path = os.path.join(home, ".ssh", "known_hosts")
    entries = parse_ssh_config(config_path)

    for entry in entries:
        if host_alias in entry.get("Host", []):
            real_host = entry.get("HostName")
            if not real_host:
                raise HTTPException(
                    status_code=500, detail="No HostName found in SSH config."
                )
            break
    else:
        raise HTTPException(
            status_code=404, detail=f"No SSH config entry found for '{host_alias}'."
        )

    # Now use the real hostname to look up the fingerprint
    output = run_command(
        ["ssh-keygen", "-F", real_host, "-f", known_hosts_path],
        allow_failure=False,
    )

    if not output:
        raise HTTPException(
            status_code=404, detail=f"No fingerprint found for host '{real_host}'."
        )

    return output


@router.get("/fingerprint/{host_alias}", response_class=JSONResponse)
async def get_host_fingerprint(host_alias: str, request: Request):
    try:
        fingerprint = get_trusted_fingerprint(host_alias)
        return {"host": host_alias, "fingerprint": fingerprint}
    except Exception as e:
        return JSONResponse(status_code=404, content={"error": str(e)})
