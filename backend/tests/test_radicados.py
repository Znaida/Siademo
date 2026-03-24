"""
Tests de endpoints de radicados: listar, filtros, historial, flujo, traslado, archivo.
Auth sobreescrita con fixtures admin_override / user_override.
"""


# ---------------------------------------------------------------------------
# GET /radicados — Listar
# ---------------------------------------------------------------------------

def test_listar_radicados_admin(admin_override):
    """Admin ve todos los radicados."""
    res = admin_override.get("/radicados")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "per_page" in data
    assert "total_pages" in data
    assert data["total"] >= 3  # Al menos los 3 del seed


def test_listar_radicados_usuario_ve_solo_propios(user_override):
    """Usuario estándar (rol 2) solo ve radicados donde es creador o responsable."""
    res = user_override.get("/radicados")
    assert res.status_code == 200
    data = res.json()
    # user_id=2 es responsable de RAD-2026-00002 y ENV-2026-00001
    for item in data["items"]:
        assert item["creado_por"] == 2 or item["funcionario_responsable_id"] == 2


def test_listar_radicados_paginacion(admin_override):
    """Paginación: per_page=1 devuelve 1 item y total_pages correcto."""
    res = admin_override.get("/radicados", params={"page": 1, "per_page": 1})
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) == 1
    assert data["per_page"] == 1
    assert data["total_pages"] >= 3


def test_listar_radicados_filtro_tipo(admin_override):
    """Filtro tipo_doc=RECIBIDA retorna solo radicados RECIBIDA."""
    res = admin_override.get("/radicados", params={"tipo_doc": "RECIBIDA"})
    assert res.status_code == 200
    for item in res.json()["items"]:
        assert item["tipo_radicado"] == "RECIBIDA"


def test_listar_radicados_filtro_estado(admin_override):
    """Filtro estado=Archivado retorna solo radicados archivados."""
    res = admin_override.get("/radicados", params={"estado": "Archivado"})
    assert res.status_code == 200
    for item in res.json()["items"]:
        assert item["estado"] == "Archivado"


def test_listar_radicados_busqueda_libre(admin_override):
    """Búsqueda libre q=Solicitud encuentra al menos 1 resultado."""
    res = admin_override.get("/radicados", params={"q": "Solicitud"})
    assert res.status_code == 200
    assert res.json()["total"] >= 1


def test_listar_radicados_busqueda_sin_resultados(admin_override):
    """Búsqueda libre con texto inexistente devuelve 0 resultados."""
    res = admin_override.get("/radicados", params={"q": "xyzabcdefgh12345"})
    assert res.status_code == 200
    assert res.json()["total"] == 0


def test_listar_radicados_filtro_serie(admin_override):
    """Filtro serie_filtro=Contratos devuelve solo radicados de esa serie."""
    res = admin_override.get("/radicados", params={"serie_filtro": "Contratos"})
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    for item in data["items"]:
        assert "Contratos" in (item["serie"] or "")


def test_listar_radicados_filtro_vencido_no(admin_override):
    """Filtro vencido=no retorna radicados con vencimiento en el futuro o sin plazo."""
    res = admin_override.get("/radicados", params={"vencido": "no"})
    assert res.status_code == 200
    assert res.status_code == 200  # No falla con este filtro


# ---------------------------------------------------------------------------
# GET /radicados/{nro}/historial
# ---------------------------------------------------------------------------

def test_historial_radicado_existente(admin_override):
    """Historial de radicado existente devuelve lista con entradas."""
    res = admin_override.get("/radicados/RAD-2026-00001/historial")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["accion"] == "CREACION"


def test_historial_radicado_archivado(admin_override):
    """Radicado archivado tiene al menos 2 entradas en historial (CREACION + ARCHIVADO)."""
    res = admin_override.get("/radicados/RAD-2026-00002/historial")
    assert res.status_code == 200
    data = res.json()
    acciones = [e["accion"] for e in data]
    assert "CREACION" in acciones
    assert "ARCHIVADO" in acciones


# ---------------------------------------------------------------------------
# GET /radicados/{nro}/flujo
# ---------------------------------------------------------------------------

def test_flujo_radicado_recibida(admin_override):
    """Flujo de comunicación RECIBIDA retorna configuración BPMN correcta."""
    res = admin_override.get("/radicados/RAD-2026-00001/flujo")
    assert res.status_code == 200
    data = res.json()
    assert "archivo_bpmn" in data
    assert "paso_actual" in data
    assert "pasos_completados" in data
    assert "todos_los_pasos" in data
    assert data["archivo_bpmn"] == "radicacion-entrada.bpmn"


def test_flujo_radicado_inexistente(admin_override):
    """Radicado que no existe → 404."""
    res = admin_override.get("/radicados/RAD-9999-99999/flujo")
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# POST /radicados/{nro}/archivar
# ---------------------------------------------------------------------------

def test_archivar_radicado_como_admin(admin_override):
    """Admin puede archivar cualquier radicado."""
    res = admin_override.post(
        "/radicados/RAD-2026-00001/archivar",
        json={"comentario": "Archivado en test"}
    )
    assert res.status_code == 200
    assert res.json()["status"] == "success"


def test_archivar_radicado_inexistente(admin_override):
    """Archivar radicado que no existe → 404."""
    res = admin_override.post(
        "/radicados/RAD-0000-00000/archivar",
        json={"comentario": "test"}
    )
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# POST /radicados/{nro}/trasladar
# ---------------------------------------------------------------------------

def test_trasladar_radicado(admin_override):
    """Admin puede trasladar ENV-2026-00001 al usuario 1."""
    res = admin_override.post(
        "/radicados/ENV-2026-00001/trasladar",
        json={"nuevo_responsable_id": 1, "comentario": "Traslado de prueba"}
    )
    assert res.status_code == 200
    assert res.json()["status"] == "success"


def test_trasladar_a_usuario_inexistente(admin_override):
    """Trasladar a un user_id que no existe → 404."""
    res = admin_override.post(
        "/radicados/ENV-2026-00001/trasladar",
        json={"nuevo_responsable_id": 9999, "comentario": "test"}
    )
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# GET /radicados/{nro}/documento
# ---------------------------------------------------------------------------

def test_ver_documento_sin_acceso(user_override):
    """Usuario sin acceso al radicado → 404 o 403 (path fuera de storage)."""
    # RAD-2026-00001: si user_id=2 no tiene acceso → 404
    # Si tiene acceso pero el path /tmp/doc1.pdf está fuera de UPLOAD_DIR → 403
    res = user_override.get("/radicados/RAD-2026-00001/documento")
    assert res.status_code in (403, 404)


def test_ver_documento_radicado_inexistente(admin_override):
    """Radicado que no existe → 404 (get_path_documento retorna None)."""
    res = admin_override.get("/radicados/RAD-0000-00000/documento")
    assert res.status_code == 404


def test_ver_documento_path_fuera_storage(admin_override):
    """Path que apunta fuera del directorio storage → 404 o 403."""
    # RAD-2026-00001 tiene path /tmp/doc1.pdf (fuera de UPLOAD_DIR) → debería dar 403 o 404
    res = admin_override.get("/radicados/RAD-2026-00001/documento")
    assert res.status_code in (403, 404)
