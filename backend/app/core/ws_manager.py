"""
WebSocket Connection Manager
Mantiene un registro en memoria de conexiones activas por usuario.
Válido para despliegue en instancia única (Azure F1/B1).
"""
import asyncio
from typing import Dict, List
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        # user_id -> lista de sockets (soporta múltiples pestañas)
        self._connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, user_id: int, ws: WebSocket):
        await ws.accept()
        self._connections.setdefault(user_id, []).append(ws)

    def disconnect(self, user_id: int, ws: WebSocket):
        conns = self._connections.get(user_id, [])
        if ws in conns:
            conns.remove(ws)
        if not conns:
            self._connections.pop(user_id, None)

    async def send_to_user(self, user_id: int, data: dict):
        conns = list(self._connections.get(user_id, []))
        dead = []
        for ws in conns:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(user_id, ws)

    def emit(self, user_id: int, data: dict):
        """Disparo desde código síncrono (CRUD). Fire-and-forget."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.send_to_user(user_id, data))
        except Exception:
            pass


manager = ConnectionManager()
