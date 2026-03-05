"""Job lifecycle management — tracks running and completed script jobs."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger("cmds2.jobs")


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Job:
    job_id: str
    script: str
    mode: str  # cloud, hybrid, cat
    category: str  # discovery, firmware, preflight, migration, ports, clean
    status: JobStatus = JobStatus.PENDING
    progress: int = 0
    message: str = ""
    exit_code: int | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    run_dir: str | None = None
    _process: asyncio.subprocess.Process | None = field(default=None, repr=False)
    log_lines: list[str] = field(default_factory=list)


class JobManager:
    """In-memory job tracker. Completed jobs persist via SQLite (written by script_runner)."""

    MAX_COMPLETED_JOBS = 200  # evict oldest completed jobs beyond this limit

    def __init__(self):
        self._jobs: dict[str, Job] = {}
        self._lock = asyncio.Lock()

    async def create(
        self, job_id: str, script: str, mode: str, category: str
    ) -> Job:
        job = Job(job_id=job_id, script=script, mode=mode, category=category)
        async with self._lock:
            self._jobs[job_id] = job
            self._evict_old_jobs()
        return job

    def _evict_old_jobs(self):
        """Remove oldest completed/failed/cancelled jobs when over the limit."""
        finished = [
            j for j in self._jobs.values()
            if j.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED)
        ]
        if len(finished) > self.MAX_COMPLETED_JOBS:
            finished.sort(key=lambda j: j.started_at)
            for j in finished[: len(finished) - self.MAX_COMPLETED_JOBS]:
                self._jobs.pop(j.job_id, None)

    async def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    async def update(self, job_id: str, **kwargs: Any):
        async with self._lock:
            job = self._jobs.get(job_id)
            if job:
                for k, v in kwargs.items():
                    if hasattr(job, k):
                        setattr(job, k, v)

    async def list_jobs(
        self, mode: str | None = None, category: str | None = None
    ) -> list[Job]:
        jobs = list(self._jobs.values())
        if mode:
            jobs = [j for j in jobs if j.mode == mode]
        if category:
            jobs = [j for j in jobs if j.category == category]
        return sorted(jobs, key=lambda j: j.started_at, reverse=True)

    async def cancel(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if not job or job.status != JobStatus.RUNNING:
            return False
        if job._process and job._process.returncode is None:
            try:
                job._process.terminate()
                await asyncio.sleep(2)
                if job._process.returncode is None:
                    job._process.kill()
            except ProcessLookupError:
                pass
        job.status = JobStatus.CANCELLED
        job.finished_at = datetime.now(timezone.utc)
        return True

    async def running_count(self) -> int:
        return sum(1 for j in self._jobs.values() if j.status == JobStatus.RUNNING)


job_manager = JobManager()
