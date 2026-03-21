import hashlib
from datetime import datetime
from fastapi import HTTPException, Request
from jose import jwt, JWTError
from app.core.config import SECRET_KEY, ALGORITHM, pwd_context
from app.core.database import get_db_connection


def firmar_resultado(resultado: int) -> str:
    texto = f"{resultado}{SECRET_KEY}"
    return hashlib.sha256(texto.encode()).hexdigest()


def verificar_password(password_plano: str, password_hash: str) -> bool:
    return pwd_context.verify(password_plano, password_hash)


async def obtener_usuario_actual(request: Request) -> dict:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token no proporcionado")
    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {"usuario": payload.get("sub"), "rol": payload.get("rol"), "id": payload.get("id_usuario")}
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")


async def obtener_admin_actual(request: Request) -> dict:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token no proporcionado")
    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        rol = payload.get("rol")
        if rol is None or rol > 1:
            raise HTTPException(status_code=403, detail="No tiene rango suficiente")
        return {"usuario": payload.get("sub"), "rol": rol, "id": payload.get("id_usuario")}
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")


def registrar_evento(usuario_id, accion: str, modulo: str, detalle: str, request: Request):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        ip_cliente = request.client.host
        cur.execute(
            "INSERT INTO auditoria (usuario_id, accion, modulo, detalle, ip_origen) VALUES (?, ?, ?, ?, ?)",
            (usuario_id, accion, modulo, detalle, ip_cliente)
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error en auditoría: {e}")


def generar_consecutivo(prefijo: str) -> str:
    anio_actual = datetime.now().year
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE secuencia_radicados SET ultimo_numero = ultimo_numero + 1 WHERE prefijo = ? AND anio = ?",
            (prefijo, anio_actual)
        )
        if cur.rowcount == 0:
            cur.execute(
                "INSERT INTO secuencia_radicados (prefijo, anio, ultimo_numero) VALUES (?, ?, 1)",
                (prefijo, anio_actual)
            )
            nuevo_valor = 1
        else:
            cur.execute(
                "SELECT ultimo_numero FROM secuencia_radicados WHERE prefijo = ? AND anio = ?",
                (prefijo, anio_actual)
            )
            nuevo_valor = cur.fetchone()[0]
        conn.commit()
        return f"{prefijo}-{anio_actual}-{nuevo_valor:05d}"
    except Exception as e:
        conn.rollback()
        print(f"Error en consecutivo: {e}")
        return None
    finally:
        cur.close()
        conn.close()
