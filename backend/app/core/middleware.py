"""
AuditMiddleware — T1.5.1
Captura automáticamente cada request HTTP y registra en la tabla auditoria:
  - usuario_id (del JWT si existe)
  - accion (METHOD + path)
  - modulo (detectado desde el path)
  - ip_origen
  - sha256_respuesta (hash del cuerpo de la respuesta)
  - timestamp

IMPORTANTE: Los logs son INMUTABLES — solo se hacen INSERT, nunca UPDATE ni DELETE.
"""
import hashlib
from datetime import datetime
from jose import jwt, JWTError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from app.core.config import SECRET_KEY, ALGORITHM
from app.core.database import get_db_connection

# Paths que NO se auditan (ruido sin valor)
SKIP_PATHS = {"/", "/docs", "/redoc", "/openapi.json", "/auth/captcha", "/favicon.ico"}
SKIP_PREFIXES = ("/docs/", "/_statics/")

# Métodos que no modifican datos — se pueden omitir para reducir volumen
# Cambia a False si quieres auditar también los GET
SOLO_ESCRITURA = True


def detectar_modulo(path: str) -> str:
    if path.startswith("/auth"):
        return "AUTH"
    if path.startswith("/admin"):
        return "ADMIN"
    if path in ("/radicar",) or path.startswith("/radicados"):
        return "VENTANILLA"
    if path.startswith("/archivo-central") or "transferir-archivo" in path:
        return "ARCHIVO"
    if path.startswith("/mis-notificaciones"):
        return "NOTIFICACIONES"
    if path.startswith("/usuarios-activos"):
        return "GESTION"
    return "SISTEMA"


def extraer_usuario_id(request: Request) -> int | None:
    try:
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return None
        token = auth.split(" ")[1]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("id_usuario")
    except (JWTError, Exception):
        return None


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method

        # Saltar paths sin valor para auditoría
        if path in SKIP_PATHS or any(path.startswith(p) for p in SKIP_PREFIXES):
            return await call_next(request)

        # Opcionalmente omitir GETs para reducir volumen
        if SOLO_ESCRITURA and method == "GET":
            return await call_next(request)

        # Ejecutar el request
        response = await call_next(request)

        # Calcular SHA-256 del cuerpo (solo para respuestas no-streaming)
        hash_respuesta = None
        content_type = response.headers.get("content-type", "")
        es_archivo = "octet-stream" in content_type or "application/pdf" in content_type

        if not es_archivo:
            try:
                body_chunks = []
                async for chunk in response.body_iterator:
                    body_chunks.append(chunk)
                body = b"".join(body_chunks)
                hash_respuesta = hashlib.sha256(body).hexdigest()
                # Reconstruir la respuesta con el body consumido
                response = Response(
                    content=body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type,
                )
            except Exception:
                pass

        # Registrar en auditoria (async-safe: SQLite es síncrono)
        try:
            usuario_id = extraer_usuario_id(request)
            accion = f"{method} {path}"
            modulo = detectar_modulo(path)
            ip = request.client.host if request.client else "desconocida"
            detalle = f"status={response.status_code}" + (
                f" sha256={hash_respuesta[:16]}..." if hash_respuesta else ""
            )

            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO auditoria
                   (usuario_id, accion, modulo, detalle, ip_origen)
                   VALUES (?, ?, ?, ?, ?)""",
                (usuario_id, accion, modulo, detalle, ip)
            )
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            # El middleware nunca debe romper el flujo principal
            print(f"[AuditMiddleware] Error al registrar: {e}")

        return response
