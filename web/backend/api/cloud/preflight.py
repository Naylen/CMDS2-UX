"""Cloud mode — Preflight validation API."""

from __future__ import annotations

import csv
import io
from pathlib import Path

from fastapi import APIRouter, Depends

from web.backend.auth.router import get_current_user
from web.backend.config import settings
from web.backend.core.script_runner import run_script
from web.backend.models.schemas import JobStartResponse, PreflightResult

router = APIRouter(prefix="/api/v1/cloud/preflight", tags=["cloud-preflight"])

_SCRIPT = str(settings.cloud_admin_dir / "meraki_preflight.sh")
_OK_FILE = settings.cloud_admin_dir / "preflight.ok"
_RUNS_DIR = settings.cloud_admin_dir / "runs" / "preflight"


@router.post("/start", response_model=JobStartResponse)
async def start_preflight(_user: str = Depends(get_current_user)):
    """Launch meraki_preflight.sh in preflight mode."""
    job = await run_script(
        _SCRIPT,
        args=["preflight"],
        mode="cloud",
        category="preflight",
    )
    return JobStartResponse(job_id=job.job_id, status=job.status.value)


@router.post("/fix-dns", response_model=JobStartResponse)
async def fix_dns(_user: str = Depends(get_current_user)):
    """Launch meraki_preflight.sh in fix-dns mode."""
    job = await run_script(_SCRIPT, args=["fix-dns"], mode="cloud", category="preflight-fix")
    return JobStartResponse(job_id=job.job_id, status=job.status.value)


@router.post("/fix-http", response_model=JobStartResponse)
async def fix_http(_user: str = Depends(get_current_user)):
    """Launch meraki_preflight.sh in fix-http mode."""
    job = await run_script(_SCRIPT, args=["fix-http"], mode="cloud", category="preflight-fix")
    return JobStartResponse(job_id=job.job_id, status=job.status.value)


def _find_latest_csv() -> Path | None:
    """Find the most recent preflight summary CSV."""
    # Check for latest symlink first
    latest_csv = _RUNS_DIR / "latest.csv"
    if latest_csv.is_file() or latest_csv.is_symlink():
        target = latest_csv.resolve()
        if target.is_file():
            return target

    # Fallback: scan run directories
    if not _RUNS_DIR.is_dir():
        return None
    runs = sorted(_RUNS_DIR.glob("run-*"), reverse=True)
    for run_dir in runs:
        for csv_file in run_dir.glob("summary*.csv"):
            return csv_file
    return None


@router.get("/results", response_model=list[PreflightResult])
async def get_results(_user: str = Depends(get_current_user)):
    """Read latest preflight summary CSV."""
    csv_path = _find_latest_csv()
    if not csv_path:
        return []

    results = []
    try:
        text = csv_path.read_text(errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            results.append(PreflightResult(
                ip=row.get("ip", ""),
                hostname=row.get("hostname", ""),
                model=row.get("model", ""),
                ios_ver=row.get("ios_ver", ""),
                dns_ok=row.get("dns_ok", ""),
                http_client_ok=row.get("http_client_ok", ""),
                ping_meraki=row.get("ping_meraki", ""),
                ready=row.get("ready", ""),
                notes=row.get("notes", ""),
            ))
    except Exception:
        pass
    return results


@router.get("/ready")
async def preflight_ready(_user: str = Depends(get_current_user)):
    """Check if preflight.ok marker exists."""
    ok = _OK_FILE.is_file() and _OK_FILE.stat().st_size > 0
    return {"ready": ok}
