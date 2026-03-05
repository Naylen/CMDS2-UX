"""Cloud mode — Firmware management and upgrade API."""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends, HTTPException, UploadFile

from web.backend.auth.router import get_current_user
from web.backend.config import settings
from web.backend.core.script_runner import run_script
from web.backend.models.schemas import (
    FirmwareImage,
    JobStartResponse,
    ScheduledJob,
)

router = APIRouter(prefix="/api/v1/cloud/firmware", tags=["cloud-firmware"])

_UPGRADE_SCRIPT = str(settings.cloud_admin_dir / "image_upgrade.sh")


def _human_size(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


@router.get("/images", response_model=list[FirmwareImage])
async def list_images(_user: str = Depends(get_current_user)):
    """List firmware images in /var/lib/tftpboot/images/."""
    images_dir = settings.firmware_dir
    if not images_dir.is_dir():
        return []

    result = []
    for f in sorted(images_dir.iterdir()):
        if f.is_file() and f.suffix in (".bin", ".SPA", ".pkg"):
            stat = f.stat()
            result.append(FirmwareImage(
                filename=f.name,
                size_bytes=stat.st_size,
                size_human=_human_size(stat.st_size),
                modified=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
            ))
    return result


@router.post("/upload")
async def upload_firmware(
    file: UploadFile, _user: str = Depends(get_current_user)
):
    """Upload a firmware image (streaming, supports multi-GB files)."""
    if not file.filename:
        raise HTTPException(400, "No filename")

    dest = settings.firmware_dir / file.filename
    settings.firmware_dir.mkdir(parents=True, exist_ok=True)

    total = 0
    async with aiofiles.open(str(dest), "wb") as out:
        while chunk := await file.read(1024 * 1024):  # 1MB chunks
            await out.write(chunk)
            total += len(chunk)

    return {
        "filename": file.filename,
        "size_bytes": total,
        "size_human": _human_size(total),
    }


@router.delete("/images/{filename}")
async def delete_image(filename: str, _user: str = Depends(get_current_user)):
    """Delete a firmware image."""
    target = settings.firmware_dir / filename
    if not target.is_file():
        raise HTTPException(404, "Image not found")
    target.unlink()
    return {"deleted": filename}


@router.post("/upgrade", response_model=JobStartResponse)
async def start_upgrade(_user: str = Depends(get_current_user)):
    """Launch image_upgrade.sh and return job ID."""
    env_file = str(settings.cloud_admin_dir / "selected_upgrade.env")
    job = await run_script(
        _UPGRADE_SCRIPT,
        args=[env_file],
        mode="cloud",
        category="firmware",
    )
    return JobStartResponse(job_id=job.job_id, status=job.status.value)


@router.post("/schedule")
async def schedule_upgrade(
    time_str: str, _user: str = Depends(get_current_user)
):
    """Schedule a firmware upgrade using the at daemon directly.

    scheduler.sh is fully interactive (dialog-based) and cannot be run
    headless.  Instead, pipe the upgrade command to `at` directly.

    time_str: 'at'-compatible time string, e.g. '2:00 AM tomorrow'
    """
    upgrade_script = _UPGRADE_SCRIPT
    sel_env = str(settings.cloud_admin_dir / "selected_upgrade.env")
    if not Path(sel_env).is_file():
        raise HTTPException(400, "No devices selected (selected_upgrade.env missing)")

    # Build the command that at will execute
    at_command = (
        f"cd {settings.cloud_admin_dir} && "
        f"CMDS_DOCKER=1 CMDS_WEB_MODE=1 "
        f"bash {upgrade_script} {sel_env}\n"
    )

    try:
        proc = await asyncio.create_subprocess_exec(
            "at", time_str,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, "CMDS_DOCKER": "1"},
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(at_command.encode()), timeout=10)
        if proc.returncode != 0:
            raise HTTPException(500, f"at failed: {stderr.decode().strip()}")
        return {"scheduled": True, "output": stderr.decode().strip()}
    except asyncio.TimeoutError:
        raise HTTPException(504, "Scheduling timed out")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/schedules", response_model=list[ScheduledJob])
async def list_schedules(_user: str = Depends(get_current_user)):
    """List scheduled at jobs."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "atq",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
        jobs = []
        for line in stdout.decode().strip().splitlines():
            parts = line.split(None, 1)
            if len(parts) >= 2:
                jobs.append(ScheduledJob(
                    job_number=parts[0],
                    scheduled_time=parts[1] if len(parts) > 1 else "",
                    command="(use at -c to view)",
                ))
        return jobs
    except Exception:
        return []
