"""WebSocket connection manager for real-time job progress streaming."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger("cmds2.ws")


class ConnectionManager:
    """Manages WebSocket connections and job subscriptions."""

    def __init__(self):
        # job_id -> set of WebSocket connections
        self._subscriptions: dict[str, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket):
        await ws.accept()

    async def disconnect(self, ws: WebSocket):
        async with self._lock:
            for job_id, subs in list(self._subscriptions.items()):
                subs.discard(ws)
                if not subs:
                    del self._subscriptions[job_id]

    async def subscribe(self, ws: WebSocket, job_id: str):
        async with self._lock:
            if job_id not in self._subscriptions:
                self._subscriptions[job_id] = set()
            self._subscriptions[job_id].add(ws)
        logger.debug("WS subscribed to job %s", job_id)

    async def unsubscribe(self, ws: WebSocket, job_id: str):
        async with self._lock:
            if job_id in self._subscriptions:
                self._subscriptions[job_id].discard(ws)

    async def broadcast(self, job_id: str, message: dict[str, Any]):
        """Send a message to all subscribers of a job."""
        async with self._lock:
            subs = self._subscriptions.get(job_id, set()).copy()
        dead: list[WebSocket] = []
        payload = json.dumps(message)
        for ws in subs:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        # Clean up dead connections
        if dead:
            async with self._lock:
                for ws in dead:
                    self._subscriptions.get(job_id, set()).discard(ws)

    async def broadcast_all(self, message: dict[str, Any]):
        """Send a message to ALL connected WebSockets (e.g., system events)."""
        async with self._lock:
            all_ws = set()
            for subs in self._subscriptions.values():
                all_ws.update(subs)
        payload = json.dumps(message)
        for ws in all_ws:
            try:
                await ws.send_text(payload)
            except Exception:
                pass


manager = ConnectionManager()
