"""Dashboard status endpoint."""

from __future__ import annotations

import json
import subprocess
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


def _check_s6_service(name: str) -> str:
    """Query s6-svstat for a service."""
    try:
        out = subprocess.run(
            ["s6-svstat", f"/run/service/{name}"],
            capture_output=True, text=True, timeout=5,
        )
        if "true" in out.stdout:
            return "active"
        return "inactive"
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
                if "SELECTED_IPS" in line or "UPGRADE_IPS" in line:
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
    services = [
        ServiceStatus(name=s, state=_check_s6_service(s)) for s in _S6_SERVICES
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
    return [
        ServiceStatus(name=s, state=_check_s6_service(s)) for s in _S6_SERVICES
    ]
