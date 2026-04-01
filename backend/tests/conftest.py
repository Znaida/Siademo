"""
Fixtures compartidos para la suite de tests de SIADE.
Estrategia de aislamiento de BD:
  - Se establece TEST_DB_PATH (env var) ANTES de importar el app.
  - get_db_connection() lee TEST_DB_PATH y usa esa ruta en todos los módulos.
  - Esto garantiza que CRUD, routers y middlewares usen la misma BD de test.
  - La BD de test se inicializa con el esquema completo + datos semilla.
"""
import os
import sqlite3
import tempfile
from datetime import datetime, timedelta

# ── Configurar env vars ANTES de cualquier import del app ──────────────────
_tmp_dir = tempfile.mkdtemp(prefix="siade_test_")
_TEST_DB = os.path.join(_tmp_dir, "test.db")
os.environ["SECRET_KEY"] = "test_secret_key_siade_pytest_2026"
os.environ["TEST_DB_PATH"] = _TEST_DB
# ──────────────────────────────────────────────────────────────────────────

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.main import app  # noqa: E402  (importar después de env vars)
from app.core.database import inicializar_db
from app.core.config import pwd_context
from app.core.security import obtener_usuario_actual, obtener_admin_actual

TEST_SECRET = "test_secret_key_siade_pytest_2026"
TEST_2FA_SECRET = "JBSWY3DPEHPK3PXP"


# ---------------------------------------------------------------------------
# Helper: generar JWT de test
# ---------------------------------------------------------------------------

def make_token(user_id: int, usuario: str, rol: int) -> str:
    payload = {
        "sub": usuario,
        "id_usuario": user_id,
        "rol": rol,
        "exp": datetime.now(tz=None) + timedelta(hours=8),
    }
    return jwt.encode(payload, TEST_SECRET, algorithm="HS256")


# ---------------------------------------------------------------------------
# Fixture: inicializar BD de test + seed (session-scoped)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """
    Inicializa el esquema SQLite en la BD de test y siembra datos mínimos.
    Usa TEST_DB_PATH establecido antes de importar el app.
    """
    inicializar_db()

    pw_hash = pwd_context.hash("TestPass123!")
    conn = sqlite3.connect(_TEST_DB)
    conn.row_factory = sqlite3.Row

    # Usuarios semilla
    conn.execute(
        "INSERT OR IGNORE INTO usuarios (id, usuario, password_hash, nombre_completo, rol_id, secret_2fa, activo) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (1, "admin_test", pw_hash, "Admin Test", 0, TEST_2FA_SECRET, 1)
    )
    conn.execute(
        "INSERT OR IGNORE INTO usuarios (id, usuario, password_hash, nombre_completo, rol_id, secret_2fa, activo) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (2, "user_test", pw_hash, "User Test", 2, TEST_2FA_SECRET, 1)
    )

    # Radicados semilla
    radicados = [
        ("RAD-2026-00001", "RECIBIDA", "Ciudadano Test", "Solicitud de prueba",
         "Contratos", "Radicado", "2026-03-01 10:00:00", 15, "2026-03-16", 1, 1, "/tmp/doc1.pdf"),
        ("RAD-2026-00002", "ENVIADA", "Entidad Externa", "Respuesta oficial",
         "Correspondencia", "Archivado", "2026-03-05 09:00:00", 5, "2026-03-10", 1, 2, "/tmp/doc2.pdf"),
        ("ENV-2026-00001", "ENVIADA", "Alcaldía", "Memorando interno",
         "Memorandos", "En Trámite", "2026-03-10 08:00:00", 10, "2026-03-20", 2, 2, "/tmp/doc3.pdf"),
        # Radicado exclusivo de admin — nunca modificado por otros tests (usado en TestHistorialAcceso)
        ("ADM-2026-00099", "RECIBIDA", "Admin Exclusivo", "Radicado de prueba IDOR",
         "Contratos", "Radicado", "2026-03-01 12:00:00", 30, "2026-04-01", 1, 1, "/tmp/adm99.pdf"),
    ]
    for r in radicados:
        conn.execute("""
            INSERT OR IGNORE INTO radicados
                (nro_radicado, tipo_radicado, nombre_razon_social, asunto, serie, estado,
                 fecha_radicacion, dias_respuesta, fecha_vencimiento, creado_por,
                 funcionario_responsable_id, path_principal)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, r)

    # Trazabilidad semilla
    trazabilidad = [
        ("RAD-2026-00001", "CREACION", "Radicado creado", 1, None, "Radicado"),
        ("RAD-2026-00002", "CREACION", "Radicado creado", 1, None, "Radicado"),
        ("RAD-2026-00002", "ARCHIVADO", "Proceso finalizado", 1, None, "Archivado"),
    ]
    for t in trazabilidad:
        conn.execute("""
            INSERT INTO trazabilidad_radicados
                (nro_radicado, accion, comentario, desde_usuario_id, hacia_usuario_id, estado_nuevo)
            VALUES (?, ?, ?, ?, ?, ?)
        """, t)

    conn.commit()
    conn.close()
    yield


# ---------------------------------------------------------------------------
# Fixture: cliente HTTP (session-scoped)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def client(setup_test_db):
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


# ---------------------------------------------------------------------------
# Fixtures de headers JWT reales
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def admin_headers():
    return {"Authorization": f"Bearer {make_token(1, 'admin_test', 0)}"}


@pytest.fixture(scope="session")
def user_headers():
    return {"Authorization": f"Bearer {make_token(2, 'user_test', 2)}"}


# ---------------------------------------------------------------------------
# Fixtures con dependency_overrides (para tests de lógica de negocio)
# Evitan que la validación JWT interfiera con los tests de endpoints.
# ---------------------------------------------------------------------------

@pytest.fixture
def admin_override(client):
    app.dependency_overrides[obtener_usuario_actual] = lambda: {"usuario": "admin_test", "rol": 0, "id": 1}
    app.dependency_overrides[obtener_admin_actual] = lambda: {"usuario": "admin_test", "rol": 0, "id": 1}
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def user_override(client):
    app.dependency_overrides[obtener_usuario_actual] = lambda: {"usuario": "user_test", "rol": 2, "id": 2}
    yield client
    app.dependency_overrides.clear()
