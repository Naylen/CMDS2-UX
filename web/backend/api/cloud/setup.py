"""Cloud mode — Setup Wizard API (meraki_discovery.env management)."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends

from web.backend.auth.router import get_current_user
from web.backend.config import settings
from web.backend.core.env_parser import read_env_masked, write_env
from web.backend.models.schemas import SetupConfig, TestResult

router = APIRouter(prefix="/api/v1/cloud/setup", tags=["cloud-setup"])

_ENV_PATH = settings.cloud_admin_dir / "meraki_discovery.env"


@router.get("", response_model=SetupConfig)
async def get_setup(_user: str = Depends(get_current_user)):
    """Read current setup config (sensitive values masked)."""
    data = read_env_masked(_ENV_PATH)
    return SetupConfig(**{k: data.get(k, "") for k in SetupConfig.model_fields})


@router.post("", response_model=SetupConfig)
async def save_setup(config: SetupConfig, _user: str = Depends(get_current_user)):
    """Write setup config to meraki_discovery.env."""
    data = config.model_dump()
    # Don't overwrite secrets with masked values
    if _ENV_PATH.is_file():
        from web.backend.core.env_parser import read_env
        existing = read_env(_ENV_PATH)
        for key in ("MERAKI_API_KEY", "SSH_PASSWORD", "ENABLE_PASSWORD"):
            if data.get(key, "").endswith("****"):
                data[key] = existing.get(key, "")
    # Remove empty keys
    data = {k: v for k, v in data.items() if v}
    write_env(_ENV_PATH, data)
    return SetupConfig(**{k: data.get(k, "") for k in SetupConfig.model_fields})


@router.post("/test-ssh", response_model=TestResult)
async def test_ssh(config: SetupConfig, _user: str = Depends(get_current_user)):
    """Test SSH connectivity to first target IP."""
    ips = config.DISCOVERY_IPS.split()
    if not ips:
        return TestResult(success=False, message="No target IPs provided")

    target = ips[0]
    username = config.SSH_USERNAME or "admin"
    password = config.SSH_PASSWORD

    try:
        proc = await asyncio.create_subprocess_exec(
            "sshpass", "-p", password,
            "ssh", "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=10",
            f"{username}@{target}",
            "show version | include uptime",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
        if proc.returncode == 0:
            return TestResult(
                success=True,
                message=f"SSH to {target} OK: {stdout.decode().strip()[:200]}"
            )
        return TestResult(
            success=False,
            message=f"SSH to {target} failed (rc={proc.returncode}): {stderr.decode().strip()[:200]}"
        )
    except asyncio.TimeoutError:
        return TestResult(success=False, message=f"SSH to {target} timed out")
    except Exception as e:
        return TestResult(success=False, message=str(e))


@router.post("/test-api", response_model=TestResult)
async def test_api(config: SetupConfig, _user: str = Depends(get_current_user)):
    """Validate Meraki API key by fetching organizations."""
    api_key = config.MERAKI_API_KEY
    if not api_key or api_key.endswith("****"):
        return TestResult(success=False, message="API key not provided")

    try:
        proc = await asyncio.create_subprocess_exec(
            "python3", "-c",
            f"import meraki; d=meraki.DashboardAPI('{api_key}',suppress_logging=True); "
            f"orgs=d.organizations.getOrganizations(); "
            f"print(f'OK: {{len(orgs)}} organization(s) accessible')",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        if proc.returncode == 0:
            return TestResult(success=True, message=stdout.decode().strip())
        return TestResult(
            success=False,
            message=f"API validation failed: {stderr.decode().strip()[:300]}"
        )
    except asyncio.TimeoutError:
        return TestResult(success=False, message="API call timed out (30s)")
    except Exception as e:
        return TestResult(success=False, message=str(e))
