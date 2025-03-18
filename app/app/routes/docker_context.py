from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from app.dependencies import templates
import subprocess
import os

router = APIRouter()


def remove_ssh_config_entry(ssh_config_path: str, host_alias: str):
    """Remove the SSH config block for a given host alias."""
    try:
        with open(ssh_config_path, "r") as f:
            lines = f.readlines()
        new_lines = []
        skip = False
        for line in lines:
            # If a block for the given host alias is detected, skip those lines.
            if line.strip().startswith("Host ") and host_alias in line:
                skip = True
                continue
            if skip and line.strip().startswith("Host "):
                skip = False
            if not skip:
                new_lines.append(line)
        with open(ssh_config_path, "w") as f:
            f.writelines(new_lines)
    except Exception as e:
        print(f"Error removing SSH config entry: {e}")


@router.get("/app/docker/context", response_class=HTMLResponse)
async def docker_context_page(request: Request):
    # List all docker contexts and filter out "default" for the dropdown.
    try:
        result = subprocess.run(
            ["docker", "context", "ls", "--format", "{{.Name}}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        all_contexts = result.stdout.strip().splitlines()
        dropdown_contexts = [ctx for ctx in all_contexts if ctx != "default"]
    except Exception as e:
        dropdown_contexts = []
        all_contexts = []
    
    # Get current default context.
    try:
        current_context_result = subprocess.run(
            ["docker", "context", "show"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        current_context = current_context_result.stdout.strip()
    except Exception as e:
        current_context = "default"
    
    # Read SSH public key from ~/.ssh/id_ed25519.pub.
    try:
        with open(os.path.expanduser("~/.ssh/id_ed25519.pub"), "r") as f:
            ssh_pubkey = f.read().strip()
    except Exception as e:
        ssh_pubkey = f"Error reading SSH public key: {e}"
    
    return templates.TemplateResponse("docker_context.html", {
        "request": request,
        "contexts": dropdown_contexts,
        "current_context": current_context,
        "ssh_pubkey": ssh_pubkey
    })


@router.post("/app/docker/context", response_class=HTMLResponse)
async def create_docker_context(
    request: Request,
    context_name: str = Form(...),
    host: str = Form(...),
    user: str = Form(...),
    port: str = Form(...)
):
    log = []
    ssh_config_path = os.path.expanduser("~/.ssh/config")
    ssh_known_hosts_path = os.path.expanduser("~/.ssh/known_hosts")
    host_alias = f"ssh.{context_name}"
    
    # Determine current default context before making changes.
    try:
        current_context_result = subprocess.run(
            ["docker", "context", "show"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        current_default = current_context_result.stdout.strip()
    except Exception:
        current_default = "default"
    
    # Ensure SSH config file exists.
    if not os.path.exists(ssh_config_path):
        open(ssh_config_path, "w").close()
    
    with open(ssh_config_path, "r") as f:
        config_content = f.read()
    
    # Check for duplicate SSH config entry.
    if host_alias in config_content:
        log.append(f"Error: SSH config entry for {host_alias} already exists.")
        return HTMLResponse(content="<br>".join(log), status_code=200)
    else:
        entry = f"\nHost {host_alias}\n    HostName {host}\n    User {user}\n    Port {port}\n"
        try:
            with open(ssh_config_path, "a") as f:
                f.write(entry)
            log.append(f"Added SSH config entry for {host_alias}.")
        except Exception as e:
            log.append(f"Error writing SSH config: {e}")
            return HTMLResponse(content="<br>".join(log), status_code=500)
    
    # Test SSH connection and update known_hosts.
    try:
        result = subprocess.run(
            ["ssh-keyscan", "-p", port, host],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode != 0 or not result.stdout.strip():
            raise Exception(result.stderr or "No output from ssh-keyscan")
        host_key = result.stdout.strip()
        
        # Check if host key is already in known_hosts.
        known_hosts_exists = False
        if os.path.exists(ssh_known_hosts_path):
            with open(ssh_known_hosts_path, "r") as f:
                known_hosts_content = f.read()
            if host in known_hosts_content:
                known_hosts_exists = True
        else:
            open(ssh_known_hosts_path, "w").close()
        
        if not known_hosts_exists:
            with open(ssh_known_hosts_path, "a") as f:
                f.write(host_key + "\n")
            log.append("Added host key to known_hosts.")
        else:
            log.append("Host key already exists in known_hosts.")
        
        # Test SSH connection (non-interactively using BatchMode).
        ssh_test = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", host_alias, "echo", "SSH_OK"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if "SSH_OK" not in ssh_test.stdout:
            raise Exception(f"SSH test failed: {ssh_test.stderr}")
        log.append("SSH connection successful.")
    except Exception as e:
        log.append(f"SSH connection error: {e}")
        # Roll back by removing the just-added SSH config entry.
        remove_ssh_config_entry(ssh_config_path, host_alias)
        return HTMLResponse(content="<br>".join(log), status_code=500)
    
    # Create Docker context if it doesn't already exist.
    try:
        result = subprocess.run(
            ["docker", "context", "ls", "--format", "{{.Name}}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        existing_contexts = result.stdout.strip().splitlines()
        if context_name in existing_contexts:
            log.append(f"Docker context '{context_name}' already exists.")
        else:
            cmd = ["docker", "context", "create", context_name, "--docker", f"host=ssh://{host_alias}"]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            log.append(f"Created Docker context '{context_name}'.")
    except Exception as e:
        log.append(f"Error creating Docker context: {e}")
        remove_ssh_config_entry(ssh_config_path, host_alias)
        return HTMLResponse(content="<br>".join(log), status_code=500)
    
    # Test Docker connection with the new context.
    try:
        subprocess.run(
            ["docker", "--context", context_name, "info"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        log.append("Docker connection successful.")
    except Exception as e:
        log.append(f"Error testing Docker connection: {e}")
        return HTMLResponse(content="<br>".join(log), status_code=500)
    
    # Only auto-switch if the current default is exactly "default".
    if current_default.strip() == "default":
        try:
            subprocess.run(
                ["docker", "context", "use", context_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            log.append(f"Switched default Docker context to: {context_name}")
        except Exception as e:
            log.append(f"Error switching default Docker context: {e}")
            return HTMLResponse(content="<br>".join(log), status_code=500)
    
    # On success, force a page refresh by sending an HX-Redirect header.
    response = HTMLResponse(content="<br>".join(log), status_code=200)
    response.headers["HX-Redirect"] = "/app/docker/context"
    return response

@router.post("/app/docker/context/default", response_class=HTMLResponse)
async def switch_default_context(request: Request, default_context: str = Form(...)):
    log = []
    try:
        subprocess.run(
            ["docker", "context", "use", default_context],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        log.append(f"Switched default Docker context to: {default_context}")
    except Exception as e:
        log.append(f"Error switching default Docker context: {e}")
        return HTMLResponse(content="<br>".join(log), status_code=500)
    
    response = HTMLResponse(content="<br>".join(log), status_code=200)
    response.headers["HX-Redirect"] = "/app/docker/context"
    return response
