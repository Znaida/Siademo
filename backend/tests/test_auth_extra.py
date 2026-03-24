"""
Tests adicionales de autenticación:
- POST /admin/setup (admin ya existe → 403)
- POST /auth/cambiar-password-inicial (debe_cambiar_password=0 → 403)
- POST /auth/cambiar-password (éxito, contraseña incorrecta, misma contraseña)
"""
import sqlite3
import pytest
from app.core.config import pwd_context


# ---------------------------------------------------------------------------
# POST /admin/setup
# ---------------------------------------------------------------------------

def test_setup_admin_ya_existe(client):
    """Si ya existe un admin (rol_id=0), setup retorna 403."""
    res = client.post("/admin/setup")
    assert res.status_code == 403
    assert "administrador" in res.json()["detail"].lower()


# ---------------------------------------------------------------------------
# POST /auth/cambiar-password-inicial
# ---------------------------------------------------------------------------

def test_cambiar_password_inicial_no_requerido(user_override):
    """Usuario que no tiene debe_cambiar_password=1 recibe 403."""
    res = user_override.post("/auth/cambiar-password-inicial", json={
        "password_actual": "TestPass123!",
        "password_nuevo": "NewPass456!",
        "password_confirmar": "NewPass456!"
    })
    assert res.status_code == 403


def test_cambiar_password_inicial_passwords_no_coinciden(setup_test_db):
    """Contraseñas que no coinciden → 400 (validación de schema)."""
    import os
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.security import obtener_usuario_actual

    # Crear un usuario con debe_cambiar_password = 1
    _TEST_DB = os.environ["TEST_DB_PATH"]
    pw_hash = pwd_context.hash("TempPass789!")
    conn = sqlite3.connect(_TEST_DB)
    conn.execute(
        "INSERT OR IGNORE INTO usuarios (usuario, password_hash, nombre_completo, rol_id, secret_2fa, activo, debe_cambiar_password) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("temp_user_init", pw_hash, "Temp User Init", 2, "JBSWY3DPEHPK3PXP", 1, 1)
    )
    conn.commit()
    conn.row_factory = sqlite3.Row
    cur = conn.execute("SELECT id FROM usuarios WHERE usuario = 'temp_user_init'")
    temp_id = cur.fetchone()[0]
    conn.close()

    with TestClient(app, raise_server_exceptions=True) as c:
        app.dependency_overrides[obtener_usuario_actual] = lambda: {
            "usuario": "temp_user_init", "rol": 2, "id": temp_id
        }
        res = c.post("/auth/cambiar-password-inicial", json={
            "password_actual": "TempPass789!",
            "password_nuevo": "NewPass456!",
            "password_confirmar": "DifferentPass789!"
        })
        app.dependency_overrides.clear()

    assert res.status_code == 400


def test_cambiar_password_inicial_exitoso(setup_test_db):
    """Usuario con debe_cambiar_password=1 puede cambiar contraseña → 200."""
    import os
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.security import obtener_usuario_actual

    _TEST_DB = os.environ["TEST_DB_PATH"]
    pw_hash = pwd_context.hash("TempPass789!")
    conn = sqlite3.connect(_TEST_DB)
    conn.execute(
        "INSERT OR IGNORE INTO usuarios (usuario, password_hash, nombre_completo, rol_id, secret_2fa, activo, debe_cambiar_password) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("temp_user_cambio", pw_hash, "Temp User Cambio", 2, "JBSWY3DPEHPK3PXP", 1, 1)
    )
    conn.commit()
    conn.row_factory = sqlite3.Row
    cur = conn.execute("SELECT id FROM usuarios WHERE usuario = 'temp_user_cambio'")
    temp_id = cur.fetchone()[0]
    conn.close()

    with TestClient(app, raise_server_exceptions=True) as c:
        app.dependency_overrides[obtener_usuario_actual] = lambda: {
            "usuario": "temp_user_cambio", "rol": 2, "id": temp_id
        }
        res = c.post("/auth/cambiar-password-inicial", json={
            "password_actual": "TempPass789!",
            "password_nuevo": "NewPass456!",
            "password_confirmar": "NewPass456!"
        })
        app.dependency_overrides.clear()

    assert res.status_code == 200
    assert "exitosamente" in res.json()["mensaje"].lower()


# ---------------------------------------------------------------------------
# POST /auth/cambiar-password
# ---------------------------------------------------------------------------

def test_cambiar_password_contrasena_actual_incorrecta(user_override):
    """Contraseña actual incorrecta → 400."""
    res = user_override.post("/auth/cambiar-password", json={
        "password_actual": "ContraseñaInvalida99!",
        "password_nuevo": "NuevaClave456!",
        "password_confirmar": "NuevaClave456!"
    })
    assert res.status_code == 400
    assert "incorrecta" in res.json()["detail"].lower()


def test_cambiar_password_confirmacion_no_coincide(user_override):
    """Confirmación diferente al nuevo → 400."""
    res = user_override.post("/auth/cambiar-password", json={
        "password_actual": "TestPass123!",
        "password_nuevo": "NuevaClave456!",
        "password_confirmar": "OtraClave789!"
    })
    assert res.status_code == 400


def test_cambiar_password_misma_que_actual(user_override):
    """Nueva contraseña igual a la actual → 400."""
    res = user_override.post("/auth/cambiar-password", json={
        "password_actual": "TestPass123!",
        "password_nuevo": "TestPass123!",
        "password_confirmar": "TestPass123!"
    })
    assert res.status_code == 400


def test_cambiar_password_exitoso(setup_test_db):
    """Cambio de contraseña con datos válidos → 200."""
    import os
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.security import obtener_usuario_actual

    # Crear un usuario dedicado para este test para no afectar otros
    _TEST_DB = os.environ["TEST_DB_PATH"]
    pw_hash = pwd_context.hash("TestPass123!")
    conn = sqlite3.connect(_TEST_DB)
    conn.execute(
        "INSERT OR IGNORE INTO usuarios (usuario, password_hash, nombre_completo, rol_id, secret_2fa, activo, debe_cambiar_password) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("user_cambio_pw", pw_hash, "User Cambio PW", 2, "JBSWY3DPEHPK3PXP", 1, 0)
    )
    conn.commit()
    conn.row_factory = sqlite3.Row
    cur = conn.execute("SELECT id FROM usuarios WHERE usuario = 'user_cambio_pw'")
    uid = cur.fetchone()[0]
    conn.close()

    with TestClient(app, raise_server_exceptions=True) as c:
        app.dependency_overrides[obtener_usuario_actual] = lambda: {
            "usuario": "user_cambio_pw", "rol": 2, "id": uid
        }
        res = c.post("/auth/cambiar-password", json={
            "password_actual": "TestPass123!",
            "password_nuevo": "NuevaClave456!",
            "password_confirmar": "NuevaClave456!"
        })
        app.dependency_overrides.clear()

    assert res.status_code == 200
    assert "exitosamente" in res.json()["mensaje"].lower()


def test_cambiar_password_sin_auth():
    """Sin token → 401."""
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app, raise_server_exceptions=True)
    res = c.post("/auth/cambiar-password", json={
        "password_actual": "x",
        "password_nuevo": "NuevaClave456!",
        "password_confirmar": "NuevaClave456!"
    })
    assert res.status_code == 401
