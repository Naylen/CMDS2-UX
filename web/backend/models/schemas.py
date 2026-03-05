"""Pydantic request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


# ── Auth ─────────────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserInfo(BaseModel):
    username: str


# ── Jobs ─────────────────────────────────────────────────────────────────
class JobResponse(BaseModel):
    job_id: str
    script: str
    mode: str
    category: str
    status: str
    progress: int
    message: str
    exit_code: int | None
    started_at: datetime
    finished_at: datetime | None


class JobStartResponse(BaseModel):
    job_id: str
    status: str


# ── Status / Dashboard ──────────────────────────────────────────────────
class ServiceStatus(BaseModel):
    name: str
    state: str  # active, inactive, unknown


class WorkflowStep(BaseModel):
    label: str
    done: bool


class DashboardStatus(BaseModel):
    services: list[ServiceStatus]
    cloud_steps: list[WorkflowStep]
    hybrid_steps: list[WorkflowStep]
    running_jobs: int
    device_counts: dict[str, int]


# ── Setup ────────────────────────────────────────────────────────────────
class SetupConfig(BaseModel):
    """Fields from meraki_discovery.env (sensitive values masked on read).

    Matches the variables written by setupwizard.sh.
    """
    MERAKI_API_KEY: str = ""
    SSH_USERNAME: str = ""
    SSH_PASSWORD: str = ""
    ENABLE_PASSWORD: str = ""
    DISCOVERY_MODE: str = ""
    DISCOVERY_IPS: str = ""
    DISCOVERY_NETWORKS: str = ""
    SSH_TEST_IP: str = ""
    DEFAULT_PRIV15_OK: str = ""
    DEFAULT_LOGIN_PRIV: str = ""
    ENABLE_TEST_OK: str = ""
    DNS_PRIMARY: str = ""
    DNS_SECONDARY: str = ""
    HTTP_CLIENT_VLAN_ID: str = ""
    HTTP_CLIENT_SOURCE_IFACE: str = ""
    MIN_IOSXE_REQUIRED: str = ""
    FW_CAT9K_FILE: str = ""
    FW_CAT9K_PATH: str = ""
    FW_CAT9K_SIZE_BYTES: str = ""
    FW_CAT9K_SIZE_H: str = ""
    FW_CAT9K_VERSION: str = ""
    FW_CAT9K_LITE_FILE: str = ""
    FW_CAT9K_LITE_PATH: str = ""
    FW_CAT9K_LITE_SIZE_BYTES: str = ""
    FW_CAT9K_LITE_SIZE_H: str = ""
    FW_CAT9K_LITE_VERSION: str = ""


class TestResult(BaseModel):
    success: bool
    message: str


# ── Discovery ────────────────────────────────────────────────────────────
class DiscoveryDevice(BaseModel):
    ip: str
    hostname: str = ""
    pid: str = ""
    serial: str = ""
    ssh: bool = False
    login: bool = False
    blacklisted: bool = False
    backup_status: str = ""
    backup_path: str = ""
    uplink_type: str = ""


class DiscoveryResults(BaseModel):
    devices: list[DiscoveryDevice]
    total: int
    eligible: int


class DeviceSelection(BaseModel):
    """IPs selected for operations."""
    ips: list[str]


# ── Firmware ─────────────────────────────────────────────────────────────
class FirmwareImage(BaseModel):
    filename: str
    size_bytes: int
    size_human: str
    modified: datetime


class ScheduledJob(BaseModel):
    job_number: str
    scheduled_time: str
    command: str


# ── Preflight ────────────────────────────────────────────────────────────
class PreflightResult(BaseModel):
    """Matches the CSV columns written by meraki_preflight.sh summary."""
    ip: str
    hostname: str = ""
    model: str = ""
    ios_ver: str = ""
    install_mode: str = ""
    req_image_type: str = ""
    min_iosxe: str = ""
    train: str = ""
    meraki_compat_ok: str = ""
    dns_ok: str = ""
    domain_lookup: str = ""
    http_client_ok: str = ""
    ping_meraki: str = ""
    ping_google: str = ""
    changed_dns: str = ""
    enabled_domain_lookup: str = ""
    changed_http_client: str = ""
    ready: str = ""
    notes: str = ""


# ── Logs ─────────────────────────────────────────────────────────────────
class LogCategory(BaseModel):
    name: str
    path: str
    run_count: int


class LogRun(BaseModel):
    run_id: str
    timestamp: str
    path: str


class LogContent(BaseModel):
    run_id: str
    lines: list[str]
    total_lines: int


# ── Clean ────────────────────────────────────────────────────────────────
class CleanPreview(BaseModel):
    files: list[str]
    total: int


# ── Utility ──────────────────────────────────────────────────────────────
class ModelEntry(BaseModel):
    model: str
    family: str
    image_type: str
    min_version: str


class BackupConfig(BaseModel):
    ip: str
    hostname: str
    filename: str
    size_bytes: int
    modified: datetime
