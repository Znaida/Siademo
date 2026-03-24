"""
Tests de endpoints de gestión: notificaciones y usuarios activos.
"""


# ---------------------------------------------------------------------------
# GET /mis-notificaciones
# ---------------------------------------------------------------------------

def test_mis_notificaciones_retorna_lista(user_override):
    """Endpoint retorna lista (vacía o con datos)."""
    res = user_override.get("/mis-notificaciones")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_mis_notificaciones_sin_auth():
    """Sin token → 401."""
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app, raise_server_exceptions=True)
    res = c.get("/mis-notificaciones")
    assert res.status_code == 401


def test_mis_notificaciones_estructura(user_override):
    """Si hay notificaciones, cada una tiene los campos esperados."""
    res = user_override.get("/mis-notificaciones")
    data = res.json()
    for item in data:
        assert "id" in item
        assert "mensaje" in item
        assert "leida" in item


# ---------------------------------------------------------------------------
# POST /mis-notificaciones/{id}/leer
# ---------------------------------------------------------------------------

def test_marcar_notificacion_leida_inexistente(user_override):
    """Marcar notificación que no existe responde ok (UPDATE 0 filas = sin error)."""
    res = user_override.post("/mis-notificaciones/99999/leer")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_marcar_notificacion_leida_sin_auth():
    """Sin token → 401."""
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app, raise_server_exceptions=True)
    res = c.post("/mis-notificaciones/1/leer")
    assert res.status_code == 401


# ---------------------------------------------------------------------------
# GET /usuarios-activos
# ---------------------------------------------------------------------------

def test_usuarios_activos_retorna_lista(user_override):
    """Endpoint retorna lista de usuarios activos."""
    res = user_override.get("/usuarios-activos")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 2


def test_usuarios_activos_estructura(user_override):
    """Cada usuario tiene id, nombre_completo y usuario."""
    res = user_override.get("/usuarios-activos")
    data = res.json()
    assert len(data) > 0
    for u in data:
        assert "id" in u
        assert "nombre_completo" in u
        assert "usuario" in u


def test_usuarios_activos_contiene_seeded(user_override):
    """Los usuarios semilla aparecen en la lista."""
    res = user_override.get("/usuarios-activos")
    usuarios = [u["usuario"] for u in res.json()]
    assert "admin_test" in usuarios
    assert "user_test" in usuarios


def test_usuarios_activos_sin_auth():
    """Sin token → 401."""
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app, raise_server_exceptions=True)
    res = c.get("/usuarios-activos")
    assert res.status_code == 401
