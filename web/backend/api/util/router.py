"""Utility endpoints — compatibility matrix, backup configs, jobs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from web.backend.auth.router import get_current_user
from web.backend.config import settings
from web.backend.core.job_manager import job_manager
from web.backend.models.schemas import BackupConfig, JobResponse, ModelEntry

router = APIRouter(prefix="/api/v1/util", tags=["utilities"])

_MODELS_FILE = settings.cloud_admin_dir / "cloud_models.json"
_MIG_DIR = settings.tftpboot_dir / "mig"


@router.get("/matrix", response_model=list[ModelEntry])
async def get_compatibility_matrix(_user: str = Depends(get_current_user)):
    """Return cloud_models.json as structured data."""
    if not _MODELS_FILE.is_file():
        return []

    try:
        raw = json.loads(_MODELS_FILE.read_text())
    except Exception:
        return []

    entries = []
    if isinstance(raw, dict):
        for family, family_data in raw.items():
            if isinstance(family_data, dict):
                models = family_data.get("models", [])
                image_type = family_data.get("image_type", "")
                min_ver = family_data.get("min_iosxe", "")
                if isinstance(models, list):
                    for model in models:
                        entries.append(ModelEntry(
                            model=model,
                            family=family,
                            image_type=image_type,
                            min_version=min_ver,
                        ))
    return entries


@router.get("/configs", response_model=list[BackupConfig])
async def list_backup_configs(_user: str = Depends(get_current_user)):
    """List switch backup configurations in /var/lib/tftpboot/mig/."""
    if not _MIG_DIR.is_dir():
        return []

    configs = []
    for f in sorted(_MIG_DIR.glob("*.cfg")):
        stat = f.stat()
        # Try to extract IP and hostname from filename
        parts = f.stem.split("_")
        ip = ""
        hostname = ""
        for p in parts:
            if all(c.isdigit() or c == "." for c in p) and p.count(".") == 3:
                ip = p
            elif not hostname:
                hostname = p

        configs.append(BackupConfig(
            ip=ip,
            hostname=hostname,
            filename=f.name,
            size_bytes=stat.st_size,
            modified=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
        ))
    return configs


@router.get("/configs/{filename}")
async def get_config_content(
    filename: str, _user: str = Depends(get_current_user)
):
    """Read a specific backup config file."""
    target = _MIG_DIR / filename
    if not target.is_file():
        raise HTTPException(404, "Config not found")
    # Prevent path traversal
    try:
        target.resolve().relative_to(_MIG_DIR.resolve())
    except ValueError:
        raise HTTPException(400, "Invalid path")

    content = target.read_text(errors="replace")
    return {"filename": filename, "content": content}


@router.get("/jobs", response_model=list[JobResponse])
async def list_jobs(
    mode: str | None = None,
    category: str | None = None,
    _user: str = Depends(get_current_user),
):
    """List all tracked jobs (in-memory)."""
    jobs = await job_manager.list_jobs(mode=mode, category=category)
    return [
        JobResponse(
            job_id=j.job_id,
            script=j.script,
            mode=j.mode,
            category=j.category,
            status=j.status.value,
            progress=j.progress,
            message=j.message,
            exit_code=j.exit_code,
            started_at=j.started_at,
            finished_at=j.finished_at,
        )
        for j in jobs
    ]


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, _user: str = Depends(get_current_user)):
    """Get details for a specific job."""
    job = await job_manager.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return JobResponse(
        job_id=job.job_id,
        script=job.script,
        mode=job.mode,
        category=job.category,
        status=job.status.value,
        progress=job.progress,
        message=job.message,
        exit_code=job.exit_code,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )


@router.get("/jobs/{job_id}/logs")
async def get_job_logs(job_id: str, _user: str = Depends(get_current_user)):
    """Get buffered log lines for a running or completed job."""
    job = await job_manager.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return {"job_id": job_id, "lines": job.log_lines, "total": len(job.log_lines)}


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str, _user: str = Depends(get_current_user)):
    """Cancel a running job."""
    ok = await job_manager.cancel(job_id)
    if not ok:
        raise HTTPException(400, "Job not running or not found")
    return {"cancelled": True, "job_id": job_id}
