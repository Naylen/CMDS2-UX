"""Admin API — service control, backups, system info."""

from __future__ import annotations

import os
import subprocess

from fastapi import APIRouter, Depends, HTTPException

from web.backend.auth.router import get_current_user
from web.backend.config import settings
from web.backend.models.schemas import ServiceStatus

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

_S6_SERVICES = ["tftpd", "httpd", "atd"]


def _s6_status(name: str) -> str:
    try:
        out = subprocess.run(
            ["s6-svstat", f"/run/service/{name}"],
            capture_output=True, text=True, timeout=5,
        )
        return "active" if "true" in out.stdout else "inactive"
    except Exception:
        return "unknown"


@router.get("/services", response_model=list[ServiceStatus])
async def list_services(_user: str = Depends(get_current_user)):
    return [ServiceStatus(name=s, state=_s6_status(s)) for s in _S6_SERVICES]


@router.post("/services/{name}")
async def control_service(
    name: str,
    action: str,  # start, stop, restart
    _user: str = Depends(get_current_user),
):
    """Start/stop/restart an s6 service."""
    if name not in _S6_SERVICES:
        raise HTTPException(400, f"Unknown service: {name}")
    if action not in ("start", "stop", "restart"):
        raise HTTPException(400, f"Unknown action: {action}")

    flag_map = {"start": "-u", "stop": "-d", "restart": "-r"}
    try:
        subprocess.run(
            ["s6-svc", flag_map[action], f"/run/service/{name}"],
            timeout=10,
        )
        return {"service": name, "action": action, "ok": True}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/backup")
async def run_backup(_user: str = Depends(get_current_user)):
    """Trigger cmds_backup.sh."""
    script = settings.server_admin_dir / "cmds_backup.sh"
    if not script.is_file():
        raise HTTPException(404, "Backup script not found")

    try:
        proc = subprocess.run(
            ["bash", str(script)],
            capture_output=True, text=True, timeout=120,
            env={**os.environ, "CMDS_DOCKER": "1"},
        )
        return {
            "exit_code": proc.returncode,
            "stdout": proc.stdout[-2000:],
            "stderr": proc.stderr[-500:],
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "Backup timed out")


@router.get("/system-info")
async def system_info(_user: str = Depends(get_current_user)):
    """Basic system information."""
    info = {}
    try:
        info["hostname"] = subprocess.run(
            ["hostname"], capture_output=True, text=True, timeout=5
        ).stdout.strip()
    except Exception:
        info["hostname"] = "unknown"

    try:
        info["uptime"] = subprocess.run(
            ["uptime", "-p"], capture_output=True, text=True, timeout=5
        ).stdout.strip()
    except Exception:
        info["uptime"] = "unknown"

    # Disk usage for tftpboot
    try:
        out = subprocess.run(
            ["df", "-h", str(settings.tftpboot_dir)],
            capture_output=True, text=True, timeout=5,
        )
        lines = out.stdout.strip().splitlines()
        if len(lines) >= 2:
            info["tftpboot_disk"] = lines[1]
    except Exception:
        pass

    return info
