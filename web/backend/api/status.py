"""Dashboard status endpoint."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, Depends

from web.backend.auth.router import get_current_user
from web.backend.config import settings
from web.backend.core.job_manager import job_manager
from web.backend.models.schemas import (
    DashboardStatus,
    ServiceStatus,
    WorkflowStep,
)

router = APIRouter(prefix="/api/v1/status", tags=["status"])

# s6 services to monitor
_S6_SERVICES = ["tftpd", "httpd", "atd"]
_S6_SVSTAT = "/command/s6-svstat"

# Cloud workflow completion markers (label -> file path)
_CLOUD_STEPS = [
    ("Setup Wizard", settings.cloud_admin_dir / "meraki_discovery.env"),
    ("Switch Discovery", settings.cloud_admin_dir / "selected_upgrade.env"),
    ("IOS-XE Upgrade", settings.cloud_admin_dir / "iosxe_upgrade.ok"),
    ("Validate IOS-XE", settings.cloud_admin_dir / "preflight.ok"),
    ("Migrate Switches", settings.cloud_admin_dir / "migration.ok"),
    ("Port Config Migration", settings.cloud_admin_dir / "iosxe_config_migration.ok"),
]

_HYBRID_STEPS = [
    ("Setup Wizard", settings.hybrid_admin_dir / "meraki_discovery.env"),
    ("Switch Discovery", settings.hybrid_admin_dir / "selected_upgrade.env"),
    ("Validate IOS-XE", settings.hybrid_admin_dir / "preflight_validated.flag"),
    ("Migrate Switches", settings.hybrid_admin_dir / "meraki_claim.log"),
]


async def _check_s6_service(name: str) -> str:
    """Query s6-svstat for a service (async)."""
    try:
        proc = await asyncio.create_subprocess_exec(
            _S6_SVSTAT, f"/run/service/{name}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
        output = stdout.decode()
        return "active" if output.startswith("up") else "inactive"
    except Exception:
        return "unknown"


def _count_devices() -> dict[str, int]:
    """Count discovered, selected, and migrated devices."""
    counts = {"discovered": 0, "selected": 0, "migrated": 0, "failed": 0}

    # Discovery results
    disc_file = settings.cloud_admin_dir / "discovery_results.json"
    if disc_file.is_file():
        try:
            devices = json.loads(disc_file.read_text())
            if isinstance(devices, list):
                counts["discovered"] = len(devices)
        except Exception:
            pass

    # Selected devices
    sel_file = settings.cloud_admin_dir / "selected_upgrade.env"
    if sel_file.is_file():
        try:
            content = sel_file.read_text()
            for line in content.splitlines():
                if "UPGRADE_SELECTED_IPS" in line:
                    ips = line.split("=", 1)[1].strip().strip("\"'()").split()
                    counts["selected"] = len([ip for ip in ips if ip])
        except Exception:
            pass

    # Migrated (meraki_memory directory)
    mem_dir = settings.cloud_admin_dir / "meraki_memory"
    if mem_dir.is_dir():
        counts["migrated"] = len(list(mem_dir.glob("*.json")))

    return counts


@router.get("", response_model=DashboardStatus)
async def get_status(_user: str = Depends(get_current_user)):
    statuses = await asyncio.gather(*[_check_s6_service(s) for s in _S6_SERVICES])
    services = [
        ServiceStatus(name=s, state=st) for s, st in zip(_S6_SERVICES, statuses)
    ]
    cloud_steps = [
        WorkflowStep(label=label, done=path.is_file() and path.stat().st_size > 0)
        for label, path in _CLOUD_STEPS
    ]
    hybrid_steps = [
        WorkflowStep(label=label, done=path.is_file() and path.stat().st_size > 0)
        for label, path in _HYBRID_STEPS
    ]
    running = await job_manager.running_count()
    counts = _count_devices()

    return DashboardStatus(
        services=services,
        cloud_steps=cloud_steps,
        hybrid_steps=hybrid_steps,
        running_jobs=running,
        device_counts=counts,
    )


@router.get("/services", response_model=list[ServiceStatus])
async def get_services(_user: str = Depends(get_current_user)):
    statuses = await asyncio.gather(*[_check_s6_service(s) for s in _S6_SERVICES])
    return [
        ServiceStatus(name=s, state=st) for s, st in zip(_S6_SERVICES, statuses)
    ]
