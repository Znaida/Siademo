"""
Tests adicionales de endpoints administrativos:
crear-usuario, equipos, dependencias, TRD, audit-logs, eventos.
"""


# ---------------------------------------------------------------------------
# POST /admin/crear-usuario
# ---------------------------------------------------------------------------

def test_crear_usuario_nuevo(admin_override):
    """Admin puede crear un usuario nuevo con rol_id=2."""
    res = admin_override.post("/admin/crear-usuario", json={
        "usuario": "funcionario_nuevo",
        "nombre_completo": "Funcionario Nuevo Test",
        "rol_id": 2
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "password_temporal" in data
    assert "secret_2fa" in data
    assert data["usuario"] == "funcionario_nuevo"


def test_crear_usuario_duplicado(admin_override):
    """Crear usuario con nombre ya existente → 400."""
    res = admin_override.post("/admin/crear-usuario", json={
        "usuario": "user_test",
        "nombre_completo": "Duplicado",
        "rol_id": 2
    })
    assert res.status_code == 400


def test_crear_usuario_rol_superadmin_prohibido(admin_override):
    """No se puede crear usuario con rol_id=0 → 403."""
    res = admin_override.post("/admin/crear-usuario", json={
        "usuario": "super_nuevo",
        "nombre_completo": "Super Nuevo",
        "rol_id": 0
    })
    assert res.status_code == 403


def test_crear_usuario_sin_auth():
    """Sin token → 401."""
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app, raise_server_exceptions=True)
    res = c.post("/admin/crear-usuario", json={"usuario": "x", "nombre_completo": "x", "rol_id": 2})
    assert res.status_code == 401


# ---------------------------------------------------------------------------
# GET /admin/listar-equipos
# ---------------------------------------------------------------------------

def test_listar_equipos_retorna_lista(admin_override):
    """Endpoint retorna lista de equipos."""
    res = admin_override.get("/admin/listar-equipos")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


# ---------------------------------------------------------------------------
# POST /admin/asignar-equipos-usuario
# ---------------------------------------------------------------------------

def test_asignar_equipos_usuario(admin_override):
    """Asignar equipos vacíos a un usuario funciona."""
    res = admin_override.post("/admin/asignar-equipos-usuario", json={
        "usuario_id": 2,
        "equipos_ids": []
    })
    assert res.status_code == 200
    assert res.json()["status"] == "success"


def test_asignar_equipos_con_equipo(admin_override):
    """Asignar equipos existentes a un usuario."""
    # Primero crear un equipo
    res_equipo = admin_override.post("/admin/crear-equipo", json={"nombre": "Equipo Para Asignar"})
    assert res_equipo.status_code == 200
    equipo_id = res_equipo.json()["id"]

    # Luego asignar
    res = admin_override.post("/admin/asignar-equipos-usuario", json={
        "usuario_id": 2,
        "equipos_ids": [equipo_id]
    })
    assert res.status_code == 200


# ---------------------------------------------------------------------------
# POST /admin/cambiar-estado-usuario
# ---------------------------------------------------------------------------

def test_cambiar_estado_usuario_desactivar(admin_override):
    """Admin puede desactivar un usuario no-admin."""
    res = admin_override.post("/admin/cambiar-estado-usuario", json={
        "user_id": 2,
        "nuevo_estado": False
    })
    assert res.status_code == 200
    assert res.json()["status"] == "success"


def test_cambiar_estado_usuario_reactivar(admin_override):
    """Admin puede reactivar un usuario."""
    res = admin_override.post("/admin/cambiar-estado-usuario", json={
        "user_id": 2,
        "nuevo_estado": True
    })
    assert res.status_code == 200


def test_cambiar_estado_usuario_inexistente(admin_override):
    """Cambiar estado de usuario inexistente → 404."""
    res = admin_override.post("/admin/cambiar-estado-usuario", json={
        "user_id": 9999,
        "nuevo_estado": False
    })
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# POST /admin/registrar-dependencia + GET /admin/listar-estructura
# ---------------------------------------------------------------------------

def test_registrar_dependencia(admin_override):
    """Registrar una dependencia nueva devuelve success."""
    res = admin_override.post("/admin/registrar-dependencia", json={
        "entidad": "Municipio Test",
        "cod_unidad": "100",
        "unidad_administrativa": "Secretaría Test",
        "cod_oficina": "101",
        "oficina_productora": "Oficina de Pruebas"
    })
    assert res.status_code == 200
    assert res.json()["status"] == "success"


def test_listar_estructura(admin_override):
    """Listar estructura retorna lista con las dependencias registradas."""
    res = admin_override.get("/admin/listar-estructura")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    # Debe contener la dependencia registrada en el test anterior
    oficinas = [d.get("oficina") for d in data]
    assert "Oficina de Pruebas" in oficinas


# ---------------------------------------------------------------------------
# POST /admin/registrar-trd + GET /admin/listar-trd
# ---------------------------------------------------------------------------

def test_registrar_trd(admin_override):
    """Registrar una serie TRD nueva devuelve success."""
    res = admin_override.post("/admin/registrar-trd", json={
        "cod_unidad": "01",
        "unidad": "Secretaría de Pruebas",
        "cod_oficina": "01.01",
        "oficina": "Oficina de Gestión",
        "cod_serie": "100",
        "nombre_serie": "Actas de Reunión",
        "cod_subserie": "100.01",
        "nombre_subserie": "Actas Ordinarias",
        "tipo_documental": "Acta",
        "soporte": "Digital",
        "extension": "PDF",
        "años_gestion": 2,
        "años_central": 3,
        "disposicion_final": "Eliminación",
        "porcentaje_seleccion": 0,
        "procedimiento": "Destrucción certificada"
    })
    assert res.status_code == 200
    assert res.json()["status"] == "success"


def test_listar_trd(admin_override):
    """Listar TRD retorna las series registradas."""
    res = admin_override.get("/admin/listar-trd")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    series = [d.get("serie") for d in data]
    assert "Actas de Reunión" in series


# ---------------------------------------------------------------------------
# GET /admin/eventos-recientes
# ---------------------------------------------------------------------------

def test_eventos_recientes_retorna_lista(admin_override):
    """Últimos eventos retorna lista con campos de auditoría."""
    res = admin_override.get("/admin/eventos-recientes")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    if data:
        assert "accion" in data[0]
        assert "modulo" in data[0]
        assert "fecha_accion" in data[0]


# ---------------------------------------------------------------------------
# GET /admin/audit-logs
# ---------------------------------------------------------------------------

def test_audit_logs_estructura(admin_override):
    """audit-logs retorna estructura paginada."""
    res = admin_override.get("/admin/audit-logs")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "per_page" in data
    assert "total_pages" in data


def test_audit_logs_filtro_modulo(admin_override):
    """Filtro por modulo=AUTH retorna solo eventos de AUTH."""
    res = admin_override.get("/admin/audit-logs", params={"modulo": "AUTH"})
    assert res.status_code == 200
    data = res.json()
    for item in data["items"]:
        assert item["modulo"] == "AUTH"


def test_audit_logs_filtro_usuario(admin_override):
    """Filtro por usuario parcial no rompe la consulta."""
    res = admin_override.get("/admin/audit-logs", params={"usuario": "admin"})
    assert res.status_code == 200
    assert "items" in res.json()


def test_audit_logs_filtro_accion(admin_override):
    """Filtro por acción parcial no rompe la consulta."""
    res = admin_override.get("/admin/audit-logs", params={"accion": "LOGIN"})
    assert res.status_code == 200


def test_audit_logs_filtro_fechas(admin_override):
    """Filtro por fecha_desde y fecha_hasta funciona."""
    res = admin_override.get("/admin/audit-logs", params={
        "fecha_desde": "2026-01-01",
        "fecha_hasta": "2026-12-31"
    })
    assert res.status_code == 200


def test_audit_logs_paginacion(admin_override):
    """Paginación con per_page=5 funciona."""
    res = admin_override.get("/admin/audit-logs", params={"per_page": 5})
    assert res.status_code == 200
    data = res.json()
    assert data["per_page"] == 5
    assert len(data["items"]) <= 5


# ---------------------------------------------------------------------------
# GET /admin/audit-logs/export
# ---------------------------------------------------------------------------

def test_audit_logs_export_csv(admin_override):
    """Exportar logs produce CSV con content-disposition."""
    res = admin_override.get("/admin/audit-logs/export")
    assert res.status_code == 200
    assert "text/csv" in res.headers.get("content-type", "")
    assert "auditoria_siade" in res.headers.get("content-disposition", "")


def test_audit_logs_export_con_filtros(admin_override):
    """Exportar con filtros no rompe la exportación."""
    res = admin_override.get("/admin/audit-logs/export", params={
        "modulo": "AUTH",
        "fecha_desde": "2026-01-01"
    })
    assert res.status_code == 200
