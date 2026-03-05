"""Log viewer API — browse and search operation logs."""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query

from web.backend.auth.router import get_current_user
from web.backend.config import settings
from web.backend.models.schemas import LogCategory, LogContent, LogRun

router = APIRouter(prefix="/api/v1/logs", tags=["logs"])

# Category -> runs subdirectory name
_CATEGORIES = {
    "discovery": "discoveryscans",
    "firmware": "",  # run-* directly under runs/
    "preflight": "preflight",
    "dns-fix": "dnsfix",
    "http-fix": "httpfix",
    "create-networks": "createnetworks",
    "migration": "migrate",
    "mgmt-ip": "mgmt_ip",
}


def _runs_base(mode: str = "cloud") -> Path:
    if mode == "hybrid":
        return settings.hybrid_admin_dir / "runs"
    return settings.cloud_admin_dir / "runs"


@router.get("/categories", response_model=list[LogCategory])
async def list_categories(
    mode: str = "cloud", _user: str = Depends(get_current_user)
):
    """List available log categories with run counts."""
    base = _runs_base(mode)
    results = []
    for name, subdir in _CATEGORIES.items():
        cat_path = base / subdir if subdir else base
        if not cat_path.is_dir():
            results.append(LogCategory(name=name, path=str(cat_path), run_count=0))
            continue
        # Count run directories
        if subdir:
            runs = [d for d in cat_path.iterdir() if d.is_dir() and not d.is_symlink()]
        else:
            runs = [d for d in cat_path.glob("run-*") if d.is_dir()]
        results.append(LogCategory(name=name, path=str(cat_path), run_count=len(runs)))
    return results


@router.get("/{category}/runs", response_model=list[LogRun])
async def list_runs(
    category: str,
    mode: str = "cloud",
    _user: str = Depends(get_current_user),
):
    """List runs within a category, newest first."""
    subdir = _CATEGORIES.get(category)
    if subdir is None:
        raise HTTPException(404, f"Unknown category: {category}")

    base = _runs_base(mode)
    cat_path = base / subdir if subdir else base

    if not cat_path.is_dir():
        return []

    # Find run directories
    if subdir:
        dirs = sorted(
            [d for d in cat_path.iterdir() if d.is_dir() and not d.is_symlink()],
            reverse=True,
        )
    else:
        dirs = sorted(cat_path.glob("run-*"), reverse=True)

    runs = []
    for d in dirs[:50]:  # Cap at 50 runs
        # Extract timestamp from directory name
        ts_match = re.search(r"(\d{14}|\d{8}-?\d{6})", d.name)
        ts = ts_match.group(1) if ts_match else d.name
        runs.append(LogRun(run_id=d.name, timestamp=ts, path=str(d)))
    return runs


@router.get("/{category}/{run_id}", response_model=LogContent)
async def get_run_logs(
    category: str,
    run_id: str,
    mode: str = "cloud",
    file: str = "",
    _user: str = Depends(get_current_user),
):
    """Read log content from a specific run."""
    subdir = _CATEGORIES.get(category)
    if subdir is None:
        raise HTTPException(404, f"Unknown category: {category}")

    base = _runs_base(mode)
    run_dir = (base / subdir / run_id) if subdir else (base / run_id)

    if not run_dir.is_dir():
        raise HTTPException(404, "Run directory not found")

    # Default to ui.status, then summary.csv, then first log file
    if file:
        target = run_dir / file
    else:
        for candidate in ["ui.status", "summary.csv", "actions.csv"]:
            target = run_dir / candidate
            if target.is_file():
                break
        else:
            # Find first readable file
            files = [f for f in run_dir.iterdir() if f.is_file()]
            if not files:
                return LogContent(run_id=run_id, lines=[], total_lines=0)
            target = files[0]

    if not target.is_file():
        raise HTTPException(404, f"File not found: {target.name}")

    # Prevent path traversal
    try:
        target.resolve().relative_to(run_dir.resolve())
    except ValueError:
        raise HTTPException(400, "Invalid file path")

    lines = target.read_text(errors="replace").splitlines()
    return LogContent(run_id=run_id, lines=lines[-2000:], total_lines=len(lines))


@router.get("/search")
async def search_logs(
    q: str = Query(..., min_length=1),
    mode: str = "cloud",
    _user: str = Depends(get_current_user),
):
    """Search across all logs for an IP or keyword."""
    base = _runs_base(mode)
    if not base.is_dir():
        return {"results": []}

    results = []
    for log_file in base.rglob("*.csv"):
        try:
            text = log_file.read_text(errors="replace")
            for i, line in enumerate(text.splitlines()):
                if q.lower() in line.lower():
                    results.append({
                        "file": str(log_file.relative_to(base)),
                        "line_number": i + 1,
                        "content": line[:500],
                    })
                    if len(results) >= 100:
                        return {"results": results, "truncated": True}
        except Exception:
            continue

    # Also search .log and .status files
    for ext in ("*.log", "*.status"):
        for log_file in base.rglob(ext):
            try:
                text = log_file.read_text(errors="replace")
                for i, line in enumerate(text.splitlines()):
                    if q.lower() in line.lower():
                        results.append({
                            "file": str(log_file.relative_to(base)),
                            "line_number": i + 1,
                            "content": line[:500],
                        })
                        if len(results) >= 100:
                            return {"results": results, "truncated": True}
            except Exception:
                continue

    return {"results": results, "truncated": False}
