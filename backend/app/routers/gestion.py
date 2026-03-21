from fastapi import APIRouter, Depends
from app.core.database import get_db_connection
from app.core.security import obtener_usuario_actual

router = APIRouter()


@router.get("/mis-notificaciones")
async def mis_notificaciones(user_info: dict = Depends(obtener_usuario_actual)):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, nro_radicado, mensaje, leida, fecha
            FROM notificaciones WHERE usuario_id = ?
            ORDER BY fecha DESC LIMIT 20
        """, (user_info['id'],))
        return [dict(r) for r in cur.fetchall()]
    finally:
        cur.close()
        conn.close()


@router.post("/mis-notificaciones/{notif_id}/leer")
async def marcar_notificacion_leida(notif_id: int, user_info: dict = Depends(obtener_usuario_actual)):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE notificaciones SET leida = 1 WHERE id = ? AND usuario_id = ?", (notif_id, user_info['id']))
        conn.commit()
        return {"status": "ok"}
    finally:
        cur.close()
        conn.close()


@router.get("/usuarios-activos")
async def listar_usuarios_activos(user_info: dict = Depends(obtener_usuario_actual)):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, nombre_completo, usuario FROM usuarios WHERE activo = 1 ORDER BY nombre_completo")
        return [dict(u) for u in cur.fetchall()]
    finally:
        cur.close()
        conn.close()
