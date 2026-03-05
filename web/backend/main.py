"""CMDS2 Web API — FastAPI application entry point."""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from web.backend.auth.jwt import decode_token
from web.backend.auth.router import router as auth_router
from web.backend.api.status import router as status_router
from web.backend.api.cloud.setup import router as cloud_setup_router
from web.backend.api.cloud.discovery import router as cloud_discovery_router
from web.backend.api.cloud.firmware import router as cloud_firmware_router
from web.backend.api.cloud.preflight import router as cloud_preflight_router
from web.backend.api.cloud.migration import router as cloud_migration_router
from web.backend.api.cloud.ports import router as cloud_ports_router
from web.backend.api.cloud.clean import router as cloud_clean_router
from web.backend.api.logs.router import router as logs_router
from web.backend.api.admin.router import router as admin_router
from web.backend.api.util.router import router as util_router
from web.backend.core.db import init_db
from web.backend.core.websocket import manager as ws_manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("cmds2.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown hooks."""
    logger.info("CMDS2 API starting up...")
    await init_db()
    logger.info("Database initialized.")
    yield
    logger.info("CMDS2 API shutting down.")


app = FastAPI(
    title="CMDS2 API",
    description="Catalyst-to-Meraki Deployment Server — Web API",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

# CORS — allow the nginx-served frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router)
app.include_router(status_router)
app.include_router(cloud_setup_router)
app.include_router(cloud_discovery_router)
app.include_router(cloud_firmware_router)
app.include_router(cloud_preflight_router)
app.include_router(cloud_migration_router)
app.include_router(cloud_ports_router)
app.include_router(cloud_clean_router)
app.include_router(logs_router)
app.include_router(admin_router)
app.include_router(util_router)


@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}


@app.websocket("/api/v1/ws")
async def websocket_endpoint(ws: WebSocket):
    """WebSocket endpoint for real-time job progress streaming.

    Client sends: {"type": "subscribe", "job_id": "..."}
    Server sends: {"type": "progress|log|complete", ...}
    """
    # Authenticate via query param or cookie
    token = ws.query_params.get("token") or ws.cookies.get("access_token")
    if token:
        payload = decode_token(token)
        if not payload or payload.get("type") != "access":
            await ws.close(code=4001, reason="Invalid token")
            return
    else:
        await ws.close(code=4001, reason="Authentication required")
        return

    await ws_manager.connect(ws)
    try:
        while True:
            data = await ws.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type", "")
            job_id = msg.get("job_id", "")

            if msg_type == "subscribe" and job_id:
                await ws_manager.subscribe(ws, job_id)
                await ws.send_text(json.dumps({
                    "type": "subscribed", "job_id": job_id,
                }))
            elif msg_type == "unsubscribe" and job_id:
                await ws_manager.unsubscribe(ws, job_id)
            elif msg_type == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))

    except WebSocketDisconnect:
        pass
    finally:
        await ws_manager.disconnect(ws)
