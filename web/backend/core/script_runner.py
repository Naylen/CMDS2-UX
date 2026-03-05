"""Async subprocess wrapper for running CMDS2 bash scripts.

Streams stdout/stderr to WebSocket subscribers and captures log lines.
Parses JSON progress lines emitted by scripts via web_progress().
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from web.backend.config import settings
from web.backend.core.job_manager import Job, JobManager, JobStatus, job_manager
from web.backend.core.websocket import manager as ws_manager

logger = logging.getLogger("cmds2.runner")

# Maximum log lines kept in memory per job
MAX_LOG_LINES = 5000


def _make_job_id(category: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{category}-{ts}"


def _base_env(mode: str) -> dict[str, str]:
    """Build environment variables for a script run."""
    env = os.environ.copy()
    env["CMDS_DOCKER"] = "1"
    env["CMDS_WEB_MODE"] = "1"
    env["TERM"] = "dumb"
    env["DIALOGRC"] = "/dev/null"
    # Disable dialog UI — scripts should detect CMDS_WEB_MODE
    env["DIALOG"] = "true"
    return env


async def run_script(
    script_path: str,
    args: list[str] | None = None,
    mode: str = "cloud",
    category: str = "general",
    cwd: str | None = None,
    env_extra: dict[str, str] | None = None,
) -> Job:
    """Launch a bash script asynchronously and stream output via WebSocket.

    Returns the Job immediately (still running). Callers can poll or subscribe.
    """
    job_id = _make_job_id(category)
    job = await job_manager.create(job_id, script_path, mode, category)

    if cwd is None:
        mode_dirs = {
            "cloud": settings.cloud_admin_dir,
            "hybrid": settings.hybrid_admin_dir,
            "cat": settings.cat_admin_dir,
        }
        cwd = str(mode_dirs.get(mode, settings.cloud_admin_dir))

    env = _base_env(mode)
    if env_extra:
        env.update(env_extra)

    cmd = ["bash", script_path] + (args or [])
    logger.info("Starting job %s: %s (cwd=%s)", job_id, " ".join(cmd), cwd)

    # Launch the background task
    asyncio.create_task(_run_and_stream(job, cmd, cwd, env))
    return job


async def _run_and_stream(
    job: Job,
    cmd: list[str],
    cwd: str,
    env: dict[str, str],
):
    """Internal: run subprocess, parse output, broadcast to WS."""
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=cwd,
            env=env,
        )
        job._process = proc
        job.status = JobStatus.RUNNING
        await ws_manager.broadcast(job.job_id, {
            "type": "started",
            "job_id": job.job_id,
            "script": job.script,
        })

        assert proc.stdout is not None
        async for raw_line in proc.stdout:
            line = raw_line.decode("utf-8", errors="replace").rstrip("\n\r")
            if not line:
                continue

            # Keep log buffer bounded
            if len(job.log_lines) < MAX_LOG_LINES:
                job.log_lines.append(line)

            # Try to parse JSON progress from web_progress()
            progress_parsed = False
            if line.startswith("{"):
                try:
                    data = json.loads(line)
                    if "pct" in data:
                        job.progress = int(data["pct"])
                        job.message = data.get("msg", "")
                        await ws_manager.broadcast(job.job_id, {
                            "type": "progress",
                            "job_id": job.job_id,
                            "pct": job.progress,
                            "msg": job.message,
                        })
                        progress_parsed = True
                except (json.JSONDecodeError, ValueError):
                    pass

            if not progress_parsed:
                await ws_manager.broadcast(job.job_id, {
                    "type": "log",
                    "job_id": job.job_id,
                    "line": line,
                })

        await proc.wait()
        job.exit_code = proc.returncode
        job.status = (
            JobStatus.COMPLETED if proc.returncode == 0 else JobStatus.FAILED
        )
    except Exception as exc:
        logger.exception("Job %s crashed: %s", job.job_id, exc)
        job.status = JobStatus.FAILED
        job.exit_code = -1
    finally:
        job.finished_at = datetime.now(timezone.utc)
        job.progress = 100 if job.status == JobStatus.COMPLETED else job.progress
        await ws_manager.broadcast(job.job_id, {
            "type": "complete",
            "job_id": job.job_id,
            "exit_code": job.exit_code,
            "status": job.status.value,
        })
        logger.info(
            "Job %s finished: status=%s exit_code=%s",
            job.job_id, job.status.value, job.exit_code,
        )
