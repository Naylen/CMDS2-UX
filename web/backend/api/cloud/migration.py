"""Cloud mode — Meraki migration API."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends

from web.backend.auth.router import get_current_user
from web.backend.config import settings
from web.backend.core.script_runner import run_script
from web.backend.models.schemas import JobStartResponse

router = APIRouter(prefix="/api/v1/cloud/migration", tags=["cloud-migration"])

_SCRIPT = str(settings.cloud_admin_dir / "migration.sh")
_MEMORY_DIR = settings.cloud_admin_dir / "meraki_memory"


@router.post("/start", response_model=JobStartResponse)
async def start_migration(_user: str = Depends(get_current_user)):
    """Launch migration.sh to claim devices into Meraki cloud."""
    # migration.sh expects a subcommand as $1 (select|map|enable|all)
    # "enable" skips the interactive switch-selection dialog and runs
    # the claim + network-map phases using the pre-selected devices.
    job = await run_script(
        _SCRIPT,
        args=["enable"],
        mode="cloud",
        category="migration",
    )
    return JobStartResponse(job_id=job.job_id, status=job.status.value)


@router.get("/inventory")
async def get_inventory(_user: str = Depends(get_current_user)):
    """Read meraki_memory/ JSON files — claimed device inventory."""
    if not _MEMORY_DIR.is_dir():
        return {"devices": [], "total": 0}

    devices = []
    for f in sorted(_MEMORY_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text())
            if isinstance(data, dict):
                devices.append(data)
            elif isinstance(data, list):
                devices.extend(data)
        except Exception:
            continue

    return {"devices": devices, "total": len(devices)}


@router.get("/network-map")
async def get_network_map(_user: str = Depends(get_current_user)):
    """Read meraki_switch_network_map.json."""
    map_file = settings.cloud_admin_dir / "meraki_switch_network_map.json"
    if not map_file.is_file():
        return {"networks": []}
    try:
        data = json.loads(map_file.read_text())
        return {"networks": data if isinstance(data, list) else [data]}
    except Exception:
        return {"networks": []}
