import asyncio
import logging
from typing import Dict, Set
from fastapi import WebSocket
from sqlalchemy.orm import Session
from app.models.deployment_log import DeploymentLog

logger = logging.getLogger("ashhub.log_stream")


class LogStreamerManager:
    """Manages active WebSocket log subscribers and streams build logs in real time."""

    def __init__(self):
        self._connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, deployment_id: int, websocket: WebSocket):
        await websocket.accept()
        if deployment_id not in self._connections:
            self._connections[deployment_id] = set()
        self._connections[deployment_id].add(websocket)
        logger.info("WebSocket client connected to deployment #%s logs stream", deployment_id)

    def disconnect(self, deployment_id: int, websocket: WebSocket):
        if deployment_id in self._connections:
            self._connections[deployment_id].discard(websocket)
            if not self._connections[deployment_id]:
                del self._connections[deployment_id]
        logger.info("WebSocket client disconnected from deployment #%s logs stream", deployment_id)

    async def broadcast_log(self, deployment_id: int, message: str, level: str = "INFO", db: Session | None = None):
        """Broadcast log line to connected WebSocket clients and save to DB."""
        # 1. Save to DB if Session provided
        if db:
            try:
                log_entry = DeploymentLog(
                    deployment_id=deployment_id,
                    log_level=level,
                    message=message
                )
                db.add(log_entry)
                db.commit()
            except Exception as e:
                logger.warning("Failed to save deployment log to DB: %s", e)

        # 2. Broadcast over WebSocket
        if deployment_id in self._connections:
            dead_sockets = set()
            for ws in self._connections[deployment_id]:
                try:
                    await ws.send_json({"deployment_id": deployment_id, "level": level, "message": message})
                except Exception:
                    dead_sockets.add(ws)

            for ws in dead_sockets:
                self._connections[deployment_id].discard(ws)


log_streamer = LogStreamerManager()
