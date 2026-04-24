"""
WebSocket endpoint — /ws
El cliente se conecta con: ws(s)://<host>/ws?token=<JWT>
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from jose import JWTError, jwt
from app.core.config import SECRET_KEY, ALGORITHM
from app.core.ws_manager import manager

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket, token: str = Query(...)):
    # Validar JWT antes de aceptar la conexión
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("id_usuario")
        if not user_id:
            await ws.close(code=1008)
            return
    except JWTError:
        await ws.close(code=1008)
        return

    await manager.connect(user_id, ws)
    try:
        while True:
            # Escuchar pings del cliente para mantener la conexión viva
            msg = await ws.receive_text()
            if msg == "ping":
                await ws.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(user_id, ws)
