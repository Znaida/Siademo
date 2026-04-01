"""
CRUD — Usuarios
Toda la lógica de acceso a BD para usuarios vive aquí.
"""
import uuid as _uuid
from fastapi import HTTPException
from app.core.database import get_db_connection, is_postgres


def crear_usuario(usuario: str, nombre_completo: str, rol_id: int,
                  password_hash: str, secret_2fa: str) -> None:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM usuarios WHERE usuario = ?", (usuario,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="El ID de usuario ya está en uso.")

        cur.execute("""
            INSERT INTO usuarios
                (usuario, password_hash, nombre_completo, rol_id, secret_2fa, activo, debe_cambiar_password)
            VALUES (?, ?, ?, ?, ?, 1, 1)
        """, (usuario, password_hash, nombre_completo, rol_id, secret_2fa))
        conn.commit()
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        ref = str(_uuid.uuid4())[:8].upper()
        print(f"[ERROR {ref}] {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor. Referencia: {ref}")
    finally:
        cur.close()
        conn.close()


def listar_usuarios() -> list:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        agg_fn = "STRING_AGG(e.nombre, ', ')" if is_postgres() else "GROUP_CONCAT(e.nombre, ', ')"
        cur.execute(f"""
            SELECT u.id, u.usuario, u.nombre_completo, u.rol_id, u.activo,
                   {agg_fn} AS grupos
            FROM usuarios u
            LEFT JOIN usuario_equipo ue ON u.id = ue.usuario_id
            LEFT JOIN equipos e ON ue.equipo_id = e.id
            WHERE u.rol_id != 0
            GROUP BY u.id, u.usuario, u.nombre_completo, u.rol_id, u.activo
            ORDER BY u.rol_id, u.nombre_completo
        """)
        return [dict(r) for r in cur.fetchall()]
    finally:
        cur.close()
        conn.close()


def cambiar_estado_usuario(user_id: int, nuevo_estado: bool) -> None:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE usuarios SET activo = ? WHERE id = ? AND rol_id != 0",
            (1 if nuevo_estado else 0, user_id)
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Usuario no encontrado o no modificable.")
        conn.commit()
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        ref = str(_uuid.uuid4())[:8].upper()
        print(f"[ERROR {ref}] {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor. Referencia: {ref}")
    finally:
        cur.close()
        conn.close()


def get_usuario_por_id(user_id: int) -> dict | None:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT id, usuario, nombre_completo, rol_id, activo FROM usuarios WHERE id = ?",
            (user_id,)
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        cur.close()
        conn.close()
