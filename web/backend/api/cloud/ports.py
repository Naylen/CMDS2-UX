"""Cloud mode — Port configuration migration API."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from web.backend.auth.router import get_current_user
from web.backend.config import settings
from web.backend.core.script_runner import run_script
from web.backend.models.schemas import JobStartResponse

router = APIRouter(prefix="/api/v1/cloud/ports", tags=["cloud-ports"])

_AUTO_SCRIPT = str(settings.cloud_admin_dir / "auto_per_port_migration.sh")
_MANUAL_SCRIPT = str(settings.cloud_admin_dir / "per_port_migration.sh")
_MGMT_IP_SCRIPT = str(settings.cloud_admin_dir / "per_switch_ip_migration.sh")


@router.post("/auto", response_model=JobStartResponse)
async def start_auto_port_migration(_user: str = Depends(get_current_user)):
    """Launch auto_per_port_migration.sh (non-interactive)."""
    env_file = str(settings.cloud_admin_dir / "meraki_discovery.env")
    job = await run_script(
        _AUTO_SCRIPT,
        args=[env_file],
        mode="cloud",
        category="ports",
    )
    return JobStartResponse(job_id=job.job_id, status=job.status.value)


@router.post("/mgmt-ip", response_model=JobStartResponse)
async def start_mgmt_ip_migration(_user: str = Depends(get_current_user)):
    """Launch per_switch_ip_migration.sh."""
    job = await run_script(
        _MGMT_IP_SCRIPT,
        mode="cloud",
        category="mgmt-ip",
    )
    return JobStartResponse(job_id=job.job_id, status=job.status.value)
