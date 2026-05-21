import asyncio
import logging
from fastapi import WebSocket

logger = logging.getLogger("fire_detection.websocket")


class ConnectionManager:
    def __init__(self):
        self.active_connections: set[WebSocket] = set()
        self.loop: asyncio.AbstractEventLoop | None = None

    async def connect(self, websocket: WebSocket):
        self.loop = asyncio.get_running_loop()
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(
            "WebSocket connected | active_connections=%s",
            len(self.active_connections),
        )

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(
            "WebSocket disconnected | active_connections=%s",
            len(self.active_connections),
        )

    async def broadcast(self, data: dict):
        if not self.active_connections:
            return

        disconnected = []

        for connection in list(self.active_connections):
            try:
                await connection.send_json(data)
            except Exception as e:
                logger.debug("WebSocket broadcast failed: %s", e)
                disconnected.append(connection)

        for conn in disconnected:
            self.disconnect(conn)

    def broadcast_threadsafe(self, data: dict):
        if not self.active_connections:
            return None
        if self.loop is None or self.loop.is_closed():
            logger.warning("WebSocket broadcast skipped: event loop is not available.")
            return None

        future = asyncio.run_coroutine_threadsafe(self.broadcast(data), self.loop)

        def _log_future_error(done_future):
            try:
                done_future.result()
            except Exception as e:
                logger.debug("Threadsafe WebSocket broadcast failed: %s", e)

        future.add_done_callback(_log_future_error)
        return future

    def connection_count(self) -> int:
        return len(self.active_connections)


manager = ConnectionManager()
