"""
Tests de endpoints de Archivo Central.
Cubre: transferir-archivo (POST) y consultar archivo-central (GET).
"""


# ---------------------------------------------------------------------------
# GET /archivo-central
# ---------------------------------------------------------------------------

def test_consultar_archivo_central_vacio(user_override):
    """Endpoint retorna lista (vacía al inicio de tests)."""
    res = user_override.get("/archivo-central")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_consultar_archivo_central_filtro_q(user_override):
    """Filtro q acepta búsqueda sin error."""
    res = user_override.get("/archivo-central", params={"q": "test"})
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_consultar_archivo_central_filtro_anio(user_override):
    """Filtro anio acepta entero sin error."""
    res = user_override.get("/archivo-central", params={"anio": 2026})
    assert res.status_code == 200


def test_consultar_archivo_central_filtro_serie(user_override):
    """Filtro serie acepta string sin error."""
    res = user_override.get("/archivo-central", params={"serie": "Contratos"})
    assert res.status_code == 200


def test_consultar_archivo_central_filtro_caja(user_override):
    """Filtro caja acepta string sin error."""
    res = user_override.get("/archivo-central", params={"caja": "CAJA-001"})
    assert res.status_code == 200


def test_consultar_archivo_central_filtro_disposicion(user_override):
    """Filtro disposicion_final acepta string sin error."""
    res = user_override.get("/archivo-central", params={"disposicion": "Conservación Total"})
    assert res.status_code == 200


def test_consultar_archivo_central_sin_auth():
    """Sin token → 401."""
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app, raise_server_exceptions=True)
    res = c.get("/archivo-central")
    assert res.status_code == 401


# ---------------------------------------------------------------------------
# POST /radicados/{nro}/transferir-archivo
# ---------------------------------------------------------------------------

def test_transferir_radicado_inexistente(admin_override):
    """Transferir radicado que no existe → 404."""
    payload = {
        "caja": "CAJA-001", "carpeta": "1",
        "folio_inicio": 1, "folio_fin": 5,
        "llaves_busqueda": "test", "observaciones": "test"
    }
    res = admin_override.post("/radicados/RAD-0000-00000/transferir-archivo", json=payload)
    assert res.status_code == 404


def test_transferir_radicado_no_archivado(admin_override):
    """Transferir radicado en estado 'En Trámite' → 400."""
    payload = {
        "caja": "CAJA-001", "carpeta": "1",
        "folio_inicio": 1, "folio_fin": 5,
        "llaves_busqueda": "", "observaciones": ""
    }
    # ENV-2026-00001 tiene estado 'En Trámite'
    res = admin_override.post("/radicados/ENV-2026-00001/transferir-archivo", json=payload)
    assert res.status_code == 400
    assert "Archivado" in res.json()["detail"]


def test_transferir_radicado_archivado(admin_override):
    """Transferir radicado con estado 'Archivado' → 200."""
    payload = {
        "caja": "CAJA-TEST", "carpeta": "1",
        "folio_inicio": 1, "folio_fin": 10,
        "llaves_busqueda": "keyword test", "observaciones": "Test transferencia"
    }
    # RAD-2026-00002 tiene estado 'Archivado'
    res = admin_override.post("/radicados/RAD-2026-00002/transferir-archivo", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "Transferido" in data["mensaje"]


def test_consultar_archivo_central_con_datos(admin_override):
    """Después de transferencia, el archivo central contiene el registro."""
    res = admin_override.get("/archivo-central")
    assert res.status_code == 200
    data = res.json()
    nros = [r["nro_radicado"] for r in data]
    assert "RAD-2026-00002" in nros


def test_transferir_sin_auth():
    """Sin token → 401."""
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app, raise_server_exceptions=True)
    payload = {"caja": "CAJA-001", "carpeta": "1", "folio_inicio": 1, "folio_fin": 5}
    res = c.post("/radicados/RAD-2026-00002/transferir-archivo", json=payload)
    assert res.status_code == 401
