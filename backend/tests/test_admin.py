"""
Tests de endpoints administrativos: KPI, stats, usuarios, dependencias, TRD.
"""


# ---------------------------------------------------------------------------
# GET /admin/kpi-dashboard
# ---------------------------------------------------------------------------

def test_kpi_dashboard_estructura(admin_override):
    """El KPI dashboard retorna todos los bloques esperados."""
    res = admin_override.get("/admin/kpi-dashboard")
    assert res.status_code == 200
    data = res.json()
    assert "volumen" in data
    assert "ans" in data
    assert "eficiencia" in data
    assert "archivo" in data
    assert "ans_breakdown" in data
    assert "ultimas" in data


def test_kpi_dashboard_volumen_campos(admin_override):
    """El bloque volumen tiene los campos numéricos correctos."""
    res = admin_override.get("/admin/kpi-dashboard")
    vol = res.json()["volumen"]
    assert "hoy" in vol
    assert "ayer" in vol
    assert "variacion_pct" in vol
    assert isinstance(vol["hoy"], int)
    assert isinstance(vol["ayer"], int)


def test_kpi_dashboard_ans_breakdown(admin_override):
    """ANS breakdown tiene cumplimiento, en_riesgo e incumplimiento."""
    res = admin_override.get("/admin/kpi-dashboard")
    breakdown = res.json()["ans_breakdown"]
    assert "cumplimiento" in breakdown
    assert "en_riesgo" in breakdown
    assert "incumplimiento" in breakdown
    for key in ["cumplimiento", "en_riesgo", "incumplimiento"]:
        assert "pct" in breakdown[key]
        assert "count" in breakdown[key]


def test_kpi_dashboard_ultimas_campos(admin_override):
    """Últimas comunicaciones tienen los campos ANS necesarios."""
    res = admin_override.get("/admin/kpi-dashboard")
    ultimas = res.json()["ultimas"]
    assert isinstance(ultimas, list)
    if ultimas:
        primera = ultimas[0]
        assert "nro_radicado" in primera
        assert "ans_label" in primera
        assert "ans_color" in primera


# ---------------------------------------------------------------------------
# GET /admin/stats-graficas
# ---------------------------------------------------------------------------

def test_stats_graficas_estructura(admin_override):
    """stats-graficas retorna barras y dona con las claves correctas."""
    res = admin_override.get("/admin/stats-graficas")
    assert res.status_code == 200
    data = res.json()
    assert "barras" in data
    assert "dona" in data
    assert "labels" in data["barras"]
    assert "series" in data["barras"]
    assert "labels" in data["dona"]
    assert "values" in data["dona"]


def test_stats_graficas_barras_7_dias(admin_override):
    """La gráfica de barras tiene exactamente 7 etiquetas de días."""
    res = admin_override.get("/admin/stats-graficas")
    labels = res.json()["barras"]["labels"]
    assert len(labels) == 7


def test_stats_graficas_series_tipos(admin_override):
    """Las series de barras incluyen los 4 tipos de radicado."""
    res = admin_override.get("/admin/stats-graficas")
    series = res.json()["barras"]["series"]
    for tipo in ["RECIBIDA", "ENVIADA", "INTERNA", "NO-RADICABLE"]:
        assert tipo in series
        assert len(series[tipo]) == 7


# ---------------------------------------------------------------------------
# GET /admin/stats-informes
# ---------------------------------------------------------------------------

def test_stats_informes_estructura(admin_override):
    """stats-informes retorna los 5 bloques esperados."""
    res = admin_override.get("/admin/stats-informes")
    assert res.status_code == 200
    data = res.json()
    assert "tendencia" in data
    assert "por_tipo" in data
    assert "por_dependencia" in data
    assert "ans_dependencia" in data
    assert "resumen" in data


def test_stats_informes_tendencia_12_meses(admin_override):
    """La tendencia tiene exactamente 12 etiquetas mensuales."""
    res = admin_override.get("/admin/stats-informes")
    tendencia = res.json()["tendencia"]
    assert len(tendencia["labels"]) == 12
    assert len(tendencia["values"]) == 12


def test_stats_informes_filtro_tipo(admin_override):
    """Filtro por tipo=RECIBIDA limita el resumen a radicados RECIBIDA."""
    res = admin_override.get("/admin/stats-informes", params={"tipo": "RECIBIDA"})
    assert res.status_code == 200
    resumen = res.json()["resumen"]
    for item in resumen:
        assert item["tipo_radicado"] == "RECIBIDA"


def test_stats_informes_filtro_fechas(admin_override):
    """Filtro por rango de fechas retorna solo radicados del período."""
    res = admin_override.get("/admin/stats-informes", params={
        "fecha_desde": "2026-03-01",
        "fecha_hasta": "2026-03-03"
    })
    assert res.status_code == 200
    resumen = res.json()["resumen"]
    for item in resumen:
        assert item["fecha_radicacion"][:10] >= "2026-03-01"
        assert item["fecha_radicacion"][:10] <= "2026-03-03"


def test_stats_informes_resumen_campos(admin_override):
    """Cada item del resumen tiene todos los campos necesarios para Excel."""
    res = admin_override.get("/admin/stats-informes")
    resumen = res.json()["resumen"]
    if resumen:
        campos = ["nro_radicado", "tipo_radicado", "nombre_razon_social",
                  "asunto", "serie", "estado", "fecha_radicacion"]
        for campo in campos:
            assert campo in resumen[0], f"Campo '{campo}' faltante en resumen"


# ---------------------------------------------------------------------------
# GET /admin/listar-usuarios
# ---------------------------------------------------------------------------

def test_listar_usuarios(admin_override):
    """Endpoint de listado devuelve usuarios no-admin (listar excluye rol 0)."""
    res = admin_override.get("/admin/listar-usuarios")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    # listar_usuarios excluye rol_id=0, así que user_test (rol 2) debe aparecer
    usuarios = [u["usuario"] for u in data]
    assert "user_test" in usuarios
    assert "admin_test" not in usuarios


# ---------------------------------------------------------------------------
# POST /admin/crear-equipo
# ---------------------------------------------------------------------------

def test_crear_equipo(admin_override):
    """Crear un equipo nuevo devuelve 200."""
    res = admin_override.post("/admin/crear-equipo", json={"nombre": "Equipo Test"})
    assert res.status_code == 200


def test_crear_equipo_nombre_vacio(admin_override):
    """Nombre de equipo vacío → 422 o 400."""
    res = admin_override.post("/admin/crear-equipo", json={"nombre": "   "})
    assert res.status_code in (400, 422)
