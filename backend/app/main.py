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


@app.get("/")
def root():
    return {"status": "ok", "sistema": "SIADE", "version": "1.0.0"}
