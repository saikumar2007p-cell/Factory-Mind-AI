"""
backend/app/websockets/stream.py

WebSocket Connection Manager for Real-Time Telemetry and Prognostics Streaming.
"""

from typing import Set, Dict, Any, List
import json
import logging
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger("factorymind.websockets")


class ConnectionManager:
    """Manages active client connections and broadcasts live simulation frames."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket client connected. Active connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket client disconnected. Active connections: {len(self.active_connections)}")

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcasts structured telemetry/inference payload to all active clients."""
        if not self.active_connections:
            return

        dead_connections = []
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Error broadcasting to WebSocket client: {e}")
                dead_connections.append(connection)

        for dead in dead_connections:
            self.disconnect(dead)


ws_manager = ConnectionManager()
