import subprocess
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

router = APIRouter()

@router.get("/available")
async def services_available():
    command = [DRY_COMMAND, "list"]
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=True
        )

        lines = result.stdout.strip().splitlines()
        service_lines = lines[1:]  # skip header
        services = []
        for line in service_lines:
            services.extend(line.strip().split())

        return JSONResponse({"services_available": sorted(services)})

    except subprocess.CalledProcessError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Command failed: {' '.join(command)}\n\n{e.output}"
        )
