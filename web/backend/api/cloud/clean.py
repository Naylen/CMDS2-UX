"""Cloud mode — Clean (reset for new batch) API."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends

from web.backend.auth.router import get_current_user
from web.backend.config import settings
from web.backend.core.script_runner import run_script
from web.backend.models.schemas import CleanPreview, JobStartResponse

router = APIRouter(prefix="/api/v1/cloud/clean", tags=["cloud-clean"])

_SCRIPT = str(settings.cloud_admin_dir / "clean.sh")

# Patterns that clean.sh removes (excluding cloud_models.json)
_CLEAN_PATTERNS = ["*.csv", "*.env", "*.json", "*.flag", "*.ok"]
_PROTECTED = {"cloud_models.json"}


@router.get("/preview", response_model=CleanPreview)
async def preview_clean(_user: str = Depends(get_current_user)):
    """List files that would be removed by clean.sh."""
    base = settings.cloud_admin_dir
    files = []
    for pattern in _CLEAN_PATTERNS:
        for f in base.glob(pattern):
            if f.name not in _PROTECTED and f.is_file():
                files.append(str(f.relative_to(base)))
    files.sort()
    return CleanPreview(files=files, total=len(files))


@router.post("/start", response_model=JobStartResponse)
async def start_clean(_user: str = Depends(get_current_user)):
    """Run clean.sh to reset for a new batch."""
    job = await run_script(
        _SCRIPT,
        args=[str(settings.cloud_admin_dir)],
        mode="cloud",
        category="clean",
    )
    return JobStartResponse(job_id=job.job_id, status=job.status.value)
