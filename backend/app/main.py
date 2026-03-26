from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import ALLOWED_ORIGINS
from app.core.database import inicializar_db
from app.core.middleware import AuditMiddleware
from app.routers import auth, radicados, admin, gestion, archivo

app = FastAPI(title="SIADE - Sistema Integral de Administración y Gestión Documental", version="1.0.0")

# CORS debe ir antes que AuditMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware de auditoría — registra automáticamente cada acción
app.add_middleware(AuditMiddleware)

inicializar_db()

app.include_router(auth.router)
app.include_router(radicados.router)
app.include_router(admin.router)
app.include_router(gestion.router)
app.include_router(archivo.router)


@app.get("/debug-db")
def debug_db():
    import os
    db_url = os.getenv("DATABASE_URL", "")
    from app.core.database import _PSYCOPG2, is_postgres
    result = {
        "DATABASE_URL_set": bool(db_url),
        "DATABASE_URL_preview": db_url[:40] if db_url else None,
        "WEBSITE_HOSTNAME": os.getenv("WEBSITE_HOSTNAME"),
        "_PSYCOPG2_at_startup": _PSYCOPG2,
        "is_postgres": is_postgres(),
        "connection_test": None,
        "connection_error": None,
        "usuarios_count": None,
    }
    try:
        from app.core.database import get_db_connection
        conn = get_db_connection()
        result["connection_test"] = type(conn).__name__
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as total FROM usuarios")
        row = cur.fetchone()
        result["usuarios_count"] = dict(row)["total"] if row else 0
        conn.close()
    except Exception as e:
        result["connection_error"] = str(e)
    return result


@app.get("/")
def root():
    return {"status": "ok", "sistema": "SIADE", "version": "1.0.0"}
