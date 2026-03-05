"""Cloud mode — Clean (reset for new batch) API."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends

from web.backend.auth.router import get_current_user
from web.backend.config import settings
from web.backend.models.schemas import CleanPreview, JobStartResponse

logger = logging.getLogger("cmds2.clean")

router = APIRouter(prefix="/api/v1/cloud/clean", tags=["cloud-clean"])

# File patterns that clean.sh removes — matching the script's behavior
_CLEAN_PATTERNS = [
    "*.csv", "*.env", "*.json", "*.flag", "*.ok",
    "discovery_results.json",
    "selected_upgrade.env",
    "selected_upgrade.json",
]
# Files that must never be removed
_PROTECTED = {"cloud_models.json", "meraki_discovery.env"}


def _find_cleanable_files() -> list[Path]:
    """List files that would be removed by a clean operation."""
    base = settings.cloud_admin_dir
    seen: set[Path] = set()
    files: list[Path] = []
    for pattern in _CLEAN_PATTERNS:
        for f in base.glob(pattern):
            if f.name not in _PROTECTED and f.is_file() and f not in seen:
                seen.add(f)
                files.append(f)
    files.sort(key=lambda f: f.name)
    return files


@router.get("/preview", response_model=CleanPreview)
async def preview_clean(_user: str = Depends(get_current_user)):
    """List files that would be removed by a clean operation."""
    base = settings.cloud_admin_dir
    files = _find_cleanable_files()
    return CleanPreview(
        files=[str(f.relative_to(base)) for f in files],
        total=len(files),
    )


@router.post("/start")
async def start_clean(_user: str = Depends(get_current_user)):
    """Clean state files to prepare for a new batch.

    clean.sh is interactive (dialog-based), so the web API performs the
    same file removal directly instead of calling the script.
    """
    files = _find_cleanable_files()
    removed = []
    errors = []
    for f in files:
        try:
            f.unlink()
            removed.append(f.name)
        except OSError as e:
            errors.append(f"{f.name}: {e}")

    logger.info("Clean: removed %d files, %d errors", len(removed), len(errors))
    return {
        "removed": len(removed),
        "errors": errors,
        "files": removed,
    }
