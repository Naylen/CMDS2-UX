"""Admin API — service control, backups, system info."""

from __future__ import annotations

import asyncio
import os

from fastapi import APIRouter, Depends, HTTPException

from web.backend.auth.router import get_current_user
from web.backend.config import settings
from web.backend.models.schemas import ServiceStatus

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

_S6_SERVICES = ["tftpd", "httpd", "atd"]
# s6 binaries live in /command (s6-overlay), not in standard PATH
_S6_SVSTAT = "/command/s6-svstat"
_S6_SVC = "/command/s6-svc"


async def _s6_status(name: str) -> str:
    try:
        proc = await asyncio.create_subprocess_exec(
            _S6_SVSTAT, f"/run/service/{name}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
        output = stdout.decode()
        # s6-svstat output: "up (pid NNN) NNN seconds" or "down NNN seconds"
        return "active" if output.startswith("up") else "inactive"
    except Exception:
        return "unknown"


@router.get("/services", response_model=list[ServiceStatus])
async def list_services(_user: str = Depends(get_current_user)):
    statuses = await asyncio.gather(*[_s6_status(s) for s in _S6_SERVICES])
    return [ServiceStatus(name=s, state=st) for s, st in zip(_S6_SERVICES, statuses)]


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
        proc = await asyncio.create_subprocess_exec(
            _S6_SVC, flag_map[action], f"/run/service/{name}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=10)
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
        proc = await asyncio.create_subprocess_exec(
            "bash", str(script),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, "CMDS_DOCKER": "1", "CMDS_WEB_MODE": "1"},
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        return {
            "exit_code": proc.returncode,
            "stdout": stdout.decode()[-2000:],
            "stderr": stderr.decode()[-500:],
        }
    except asyncio.TimeoutError:
        raise HTTPException(504, "Backup timed out")


@router.get("/system-info")
async def system_info(_user: str = Depends(get_current_user)):
    """Basic system information."""
    info = {}

    async def _run_cmd(cmd: list[str]) -> str:
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
            return stdout.decode().strip()
        except Exception:
            return "unknown"

    hostname, uptime, disk = await asyncio.gather(
        _run_cmd(["hostname"]),
        _run_cmd(["uptime", "-p"]),
        _run_cmd(["df", "-h", str(settings.tftpboot_dir)]),
    )

    info["hostname"] = hostname
    info["uptime"] = uptime
    disk_lines = disk.strip().splitlines()
    if len(disk_lines) >= 2:
        info["tftpboot_disk"] = disk_lines[1]

    return info
