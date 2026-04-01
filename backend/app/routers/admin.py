import os
import secrets
import string
from io import BytesIO
from typing import List, Optional
import pandas as pd
import pyotp
from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Depends, Query
from fastapi.responses import FileResponse, StreamingResponse
from app.core.config import pwd_context
from app.core.database import get_db_connection
from app.core.security import obtener_admin_actual, registrar_evento
from app.schemas.usuario import UserCreate, UserCreateAdmin, UserStatusUpdate
from app.schemas.admin import DependenciaCreate, TRDCreate, EquipoCreate, AsignacionEquipos
from app.crud.usuario import crear_usuario as crud_crear_usuario, listar_usuarios as crud_listar_usuarios, cambiar_estado_usuario as crud_cambiar_estado
from app.crud.auditoria import consultar_logs, exportar_logs_csv

router = APIRouter(prefix="/admin")


@router.post("/crear-usuario")
async def crear_usuario(request: Request, data: UserCreateAdmin, admin_info: dict = Depends(obtener_admin_actual)):
    if data.rol_id == 0:
        raise HTTPException(status_code=403, detail="No se permite la creación de Super Usuarios adicionales.")
    if data.rol_id == 1 and admin_info['rol'] != 0:
        registrar_evento(admin_info['id'], 'SECURITY_VIOLATION', 'ADMIN', f"Intento fallido de crear Admin por {admin_info['usuario']}", request)
        raise HTTPException(status_code=403, detail="Permisos insuficientes.")

    alfabeto = string.ascii_letters + string.digits
    password_temporal = ''.join(secrets.choice(alfabeto) for _ in range(10))
    hashed_pw = pwd_context.hash(password_temporal)
    secret_2fa = pyotp.random_base32()

    crud_crear_usuario(data.usuario, data.nombre_completo, data.rol_id, hashed_pw, secret_2fa)
    registrar_evento(admin_info['id'], 'CREATE_USER', 'ADMIN',
                     f"Nuevo funcionario: {data.usuario} (Rol: {data.rol_id})", request)
    return {
        "status": "success",
        "usuario": data.usuario,
        "message": "Usuario creado. Comparte la contraseña temporal con el funcionario.",
        "secret_2fa": secret_2fa,
        "password_temporal": password_temporal,
        "aviso": "El usuario deberá cambiar su contraseña en el primer inicio de sesión."
    }


@router.post("/crear-equipo")
async def crear_equipo(request: Request, data: EquipoCreate, admin_info: dict = Depends(obtener_admin_actual)):
    nombre_limpio = data.nombre.strip()
    if not nombre_limpio:
        raise HTTPException(status_code=400, detail="El nombre del grupo no puede estar vacío")

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM equipos WHERE nombre LIKE ?", (nombre_limpio,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail=f"El grupo '{nombre_limpio}' ya existe.")

        cur.execute("INSERT INTO equipos (nombre) VALUES (?)", (nombre_limpio,))
        equipo_id = cur.lastrowid
        conn.commit()
        registrar_evento(admin_info['id'], 'CREATE_TEAM', 'ADMIN', f"Nuevo grupo: {nombre_limpio}", request)
        return {"status": "success", "id": equipo_id, "message": "Grupo creado exitosamente"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


@router.get("/listar-equipos")
async def listar_equipos(admin_info: dict = Depends(obtener_admin_actual)):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, nombre FROM equipos ORDER BY nombre ASC")
        return [dict(r) for r in cur.fetchall()]
    finally:
        cur.close()
        conn.close()


@router.post("/asignar-equipos-usuario")
async def asignar_equipos(request: Request, data: AsignacionEquipos, admin_info: dict = Depends(obtener_admin_actual)):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM usuario_equipo WHERE usuario_id = ?", (data.usuario_id,))
        for eid in data.equipos_ids:
            cur.execute("INSERT INTO usuario_equipo (usuario_id, equipo_id) VALUES (?, ?)", (data.usuario_id, eid))
        conn.commit()
        registrar_evento(admin_info['id'], 'ASSIGN_TEAM', 'ADMIN', f"Equipos para User ID: {data.usuario_id}", request)
        return {"status": "success", "message": "Equipos actualizados correctamente"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


@router.post("/cambiar-estado-usuario")
async def cambiar_estado_usuario(request: Request, data: UserStatusUpdate, admin_info: dict = Depends(obtener_admin_actual)):
    crud_cambiar_estado(data.user_id, data.nuevo_estado)
    registrar_evento(admin_info['id'], 'USER_STATUS_CHANGE', 'ADMIN', f"ID: {data.user_id}", request)
    return {"status": "success"}


@router.post("/registrar-dependencia")
async def registrar_dependencia(request: Request, data: DependenciaCreate, admin_info: dict = Depends(obtener_admin_actual)):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO estructura_organica (entidad, unidad, oficina, depende_de) VALUES (?, ?, ?, ?)",
                (data.entidad, data.unidad_administrativa, data.oficina_productora, data.relacion_jerarquica))
    conn.commit()
    registrar_evento(admin_info['id'], 'CONFIG_ESTRUCTURA', 'ADMIN', f"Nueva: {data.oficina_productora}", request)
    cur.close()
    conn.close()
    return {"status": "success"}


@router.post("/registrar-trd")
async def registrar_trd(request: Request, data: TRDCreate, admin_info: dict = Depends(obtener_admin_actual)):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO trd (cod_unidad, unidad, cod_oficina, oficina, cod_serie, nombre_serie,
                cod_subserie, nombre_subserie, tipo_documental, soporte, extension,
                años_gestion, años_central, disposicion_final, porcentaje_seleccion, procedimiento)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (data.cod_unidad, data.unidad, data.cod_oficina, data.oficina, data.cod_serie, data.nombre_serie,
              data.cod_subserie, data.nombre_subserie, data.tipo_documental, data.soporte, data.extension,
              data.años_gestion, data.años_central, data.disposicion_final, data.porcentaje_seleccion, data.procedimiento))
        conn.commit()
        registrar_evento(admin_info['id'], 'CONFIG_TRD', 'ADMIN', f"Serie guardada: {data.nombre_serie}", request)
        return {"status": "success", "message": "Serie documental registrada exitosamente"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


@router.get("/descargar-plantilla-trd")
async def descargar_plantilla_trd():
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    file_path = os.path.join(BASE_DIR, "..", "storage", "plantilla_trd.xlsx")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="La plantilla no se encuentra en el servidor.")
    return FileResponse(path=file_path, filename="Plantilla_Oficial_TRD_SIADE.xlsx",
                        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@router.post("/importar-trd-excel")
async def importar_trd_excel(request: Request, file: UploadFile = File(...), admin_info: dict = Depends(obtener_admin_actual)):
    try:
        df = pd.read_excel(BytesIO(await file.read()), sheet_name='datos')
        conn = get_db_connection()
        cur = conn.cursor()
        count = 0
        for _, row in df.iterrows():
            cur.execute("""
                INSERT INTO trd (cod_unidad, unidad, cod_oficina, oficina, cod_serie, nombre_serie,
                    cod_subserie, nombre_subserie, tipo_documental, soporte, extension,
                    años_gestion, años_central, disposicion_final, porcentaje_seleccion, procedimiento)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (str(row.get('CodigoUnidad', '')), str(row.get('Unidad', '')),
                  str(row.get('CodigoOficina', '')), str(row.get('Oficina', '')),
                  str(row.get('CodigoSerie', '')), str(row.get('Serie', '')),
                  str(row.get('CodigoSubserie', '')), str(row.get('Subserie', '')),
                  str(row.get('TipoDocumental', '')), str(row.get('Soporte', 'Digital')),
                  str(row.get('Extension', 'PDF')),
                  int(row.get('Gestion', 0)) if row.get('Gestion') else 0,
                  int(row.get('Central', 0)) if row.get('Central') else 0,
                  str(row.get('Disposicion', 'Conservación Total')),
                  int(row.get('Seleccion', 0)) if row.get('Seleccion') else 0,
                  str(row.get('Procedimiento', ''))))
            count += 1
        conn.commit()
        cur.close()
        conn.close()
        return {"status": "success", "count": count}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/importar-estructura-excel")
async def importar_estructura_excel(request: Request, file: UploadFile = File(...), admin_info: dict = Depends(obtener_admin_actual)):
    try:
        df = pd.read_excel(BytesIO(await file.read()))
        conn = get_db_connection()
        cur = conn.cursor()
        count = 0
        for _, row in df.iterrows():
            cur.execute("INSERT INTO estructura_organica (entidad, unidad, oficina, depende_de) VALUES (?, ?, ?, ?)",
                        (str(row['Entidad']), str(row['Unidad']), str(row['Oficina']), str(row.get('DependeDe', 'Nivel Raíz'))))
            count += 1
        conn.commit()
        cur.close()
        conn.close()
        return {"status": "success", "count": count}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/listar-estructura")
async def listar_estructura(admin_info: dict = Depends(obtener_admin_actual)):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT unidad, oficina, depende_de FROM estructura_organica ORDER BY unidad ASC")
    res = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in res]


@router.get("/listar-trd")
async def listar_trd(admin_info: dict = Depends(obtener_admin_actual)):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT cod_serie AS codigo, unidad, oficina, nombre_serie AS serie,
                   cod_subserie, nombre_subserie AS subserie, tipo_documental, soporte,
                   años_gestion AS ag, años_central AS ac, disposicion_final AS disposicion
            FROM trd ORDER BY cod_serie ASC
        """)
        return [dict(r) for r in cur.fetchall()]
    finally:
        cur.close()
        conn.close()


@router.get("/listar-usuarios")
async def listar_usuarios(admin_info: dict = Depends(obtener_admin_actual)):
    return crud_listar_usuarios()


@router.get("/kpi-dashboard")
async def obtener_kpi_dashboard(admin_info: dict = Depends(obtener_admin_actual)):
    """KPIs para las tarjetas del Panel de Control."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Fechas como parámetros (compatible SQLite y PostgreSQL)
        from datetime import date, timedelta as _td
        _hoy = date.today().isoformat()
        _ayer = (date.today() - _td(days=1)).isoformat()
        _tres_dias = (date.today() + _td(days=3)).isoformat()
        _inicio_mes = date.today().replace(day=1).isoformat()

        # --- Volumen de radicación ---
        _hoy_siguiente = (date.today() + _td(days=1)).isoformat()
        _ayer_siguiente = date.today().isoformat()
        cur.execute("SELECT COUNT(*) as cnt FROM radicados WHERE fecha_radicacion >= ? AND fecha_radicacion < ?", (_hoy, _hoy_siguiente))
        hoy = cur.fetchone()['cnt']
        cur.execute("SELECT COUNT(*) as cnt FROM radicados WHERE fecha_radicacion >= ? AND fecha_radicacion < ?", (_ayer, _ayer_siguiente))
        ayer = cur.fetchone()['cnt']
        variacion = round(((hoy - ayer) / ayer * 100), 1) if ayer > 0 else 0

        # --- Cumplimiento ANS ---
        cur.execute("SELECT COUNT(*) as cnt FROM radicados WHERE estado NOT IN ('Archivado','En Archivo Central')")
        activos = cur.fetchone()['cnt']
        cur.execute("""SELECT COUNT(*) as cnt FROM radicados
                       WHERE estado NOT IN ('Archivado','En Archivo Central')
                       AND (fecha_vencimiento IS NULL OR fecha_vencimiento >= ?)""", (_hoy,))
        dentro_plazo = cur.fetchone()['cnt']
        pct_ans = round((dentro_plazo / activos * 100), 1) if activos > 0 else 100.0
        cur.execute("SELECT COUNT(*) as cnt FROM radicados WHERE fecha_vencimiento = ?", (_hoy,))
        vencen_hoy = cur.fetchone()['cnt']

        # --- Eficiencia operativa ---
        cur.execute("SELECT COUNT(*) as cnt FROM radicados")
        total = cur.fetchone()['cnt']
        cur.execute("SELECT COUNT(*) as cnt FROM radicados WHERE estado IN ('Archivado','En Archivo Central')")
        completados = cur.fetchone()['cnt']
        pct_eficiencia = round((completados / total * 100), 1) if total > 0 else 0.0
        cur.execute("SELECT COUNT(*) as cnt FROM radicados WHERE estado = 'En Trámite'")
        en_tramite = cur.fetchone()['cnt']

        # --- Archivo digital ---
        cur.execute("SELECT COUNT(*) as cnt FROM archivo_central")
        archivados = cur.fetchone()['cnt']
        cur.execute("SELECT COUNT(*) as cnt FROM archivo_central WHERE fecha_transferencia >= ?", (_inicio_mes,))
        archivados_mes = cur.fetchone()['cnt']
        pct_archivo_mes = round((archivados_mes / archivados * 100), 1) if archivados > 0 else 0.0

        # --- ANS breakdown (cumplimiento / en riesgo / incumplimiento) ---
        cur.execute("""SELECT COUNT(*) as cnt FROM radicados
                       WHERE estado NOT IN ('Archivado','En Archivo Central')
                       AND fecha_vencimiento IS NOT NULL
                       AND fecha_vencimiento < ?""", (_hoy,))
        vencidos = cur.fetchone()['cnt']
        cur.execute("""SELECT COUNT(*) as cnt FROM radicados
                       WHERE estado NOT IN ('Archivado','En Archivo Central')
                       AND fecha_vencimiento BETWEEN ? AND ?""", (_hoy, _tres_dias))
        en_riesgo = cur.fetchone()['cnt']
        a_tiempo = max(0, activos - vencidos - en_riesgo)
        pct_cumplimiento  = round(a_tiempo  / activos * 100, 1) if activos > 0 else 100.0
        pct_en_riesgo     = round(en_riesgo / activos * 100, 1) if activos > 0 else 0.0
        pct_incumplimiento = round(vencidos / activos * 100, 1) if activos > 0 else 0.0

        # --- Últimas 5 comunicaciones ---
        cur.execute("""
            SELECT r.nro_radicado, r.nombre_razon_social, r.asunto,
                   r.estado, r.fecha_vencimiento, r.tipo_radicado
            FROM radicados r
            ORDER BY r.id DESC LIMIT 5
        """)
        from datetime import date
        hoy_date = date.today()
        ultimas = []
        for row in cur.fetchall():
            r = dict(row)
            fv = r.get('fecha_vencimiento')
            if fv:
                try:
                    fv_date = date.fromisoformat(fv[:10])
                    diff = (fv_date - hoy_date).days
                    if r['estado'] in ('Archivado', 'En Archivo Central'):
                        ans_label, ans_color = 'A tiempo', 'green'
                    elif diff < 0:
                        ans_label, ans_color = f'{diff} días', 'red'
                    elif diff == 0:
                        ans_label, ans_color = 'Vence hoy', 'red'
                    elif diff <= 3:
                        ans_label, ans_color = f'{diff} días', 'yellow'
                    else:
                        ans_label, ans_color = 'A tiempo', 'green'
                except Exception:
                    ans_label, ans_color = '---', 'gray'
            else:
                ans_label, ans_color = 'Sin plazo', 'gray'
            r['ans_label'] = ans_label
            r['ans_color'] = ans_color
            ultimas.append(r)

        return {
            "volumen":    {"hoy": hoy, "ayer": ayer, "variacion_pct": variacion},
            "ans":        {"pct": pct_ans, "vencen_hoy": vencen_hoy},
            "eficiencia": {"pct": pct_eficiencia, "en_tramite": en_tramite},
            "archivo":    {"total": archivados, "mes": archivados_mes, "pct_mes": pct_archivo_mes},
            "ans_breakdown": {
                "cumplimiento":   {"pct": pct_cumplimiento,   "count": a_tiempo},
                "en_riesgo":      {"pct": pct_en_riesgo,      "count": en_riesgo},
                "incumplimiento": {"pct": pct_incumplimiento, "count": vencidos}
            },
            "ultimas": ultimas
        }
    finally:
        cur.close()
        conn.close()


@router.get("/stats-graficas")
async def obtener_stats_graficas(admin_info: dict = Depends(obtener_admin_actual)):
    """Datos para Chart.js: últimos 7 días por tipo + distribución por estado."""
    from datetime import date, timedelta
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # --- Barras: últimos 7 días por tipo de radicado ---
        hoy = date.today()
        dias = [(hoy - timedelta(days=i)) for i in range(6, -1, -1)]
        labels_dias = [d.strftime("%d/%m") for d in dias]

        tipos = ["RECIBIDA", "ENVIADA", "INTERNA", "NO-RADICABLE"]
        series_barras = {}
        for tipo in tipos:
            serie = []
            for d in dias:
                d_next = (d + timedelta(days=1)).isoformat()
                cur.execute(
                    "SELECT COUNT(*) as cnt FROM radicados WHERE tipo_radicado = ? AND fecha_radicacion >= ? AND fecha_radicacion < ?",
                    (tipo, d.isoformat(), d_next)
                )
                serie.append(cur.fetchone()['cnt'])
            series_barras[tipo] = serie

        # --- Dona: distribución actual por estado ---
        cur.execute("""
            SELECT estado, COUNT(*) as cnt FROM radicados
            GROUP BY estado ORDER BY cnt DESC
        """)
        estados_rows = cur.fetchall()
        estados_labels = [r['estado'] for r in estados_rows]
        estados_values = [r['cnt'] for r in estados_rows]

        return {
            "barras": {
                "labels": labels_dias,
                "series": series_barras
            },
            "dona": {
                "labels": estados_labels,
                "values": estados_values
            }
        }
    finally:
        cur.close()
        conn.close()


@router.get("/stats-informes")
async def obtener_stats_informes(
    admin_info: dict = Depends(obtener_admin_actual),
    fecha_desde: Optional[str] = Query(None),
    fecha_hasta: Optional[str] = Query(None),
    tipo: Optional[str] = Query(None),
    dependencia: Optional[str] = Query(None)
):
    """Datos para la sección Informes: tendencia mensual, por tipo, por dependencia, ANS."""
    from datetime import date, timedelta
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Construir WHERE base con filtros
        condiciones = []
        params_base = []
        if fecha_desde:
            condiciones.append("fecha_radicacion >= ?")
            params_base.append(fecha_desde)
        if fecha_hasta:
            condiciones.append("fecha_radicacion <= ?")
            params_base.append(fecha_hasta + " 23:59:59")
        if tipo:
            condiciones.append("tipo_radicado = ?")
            params_base.append(tipo)
        if dependencia:
            condiciones.append("seccion_responsable LIKE ?")
            params_base.append(f"%{dependencia}%")
        where = ("WHERE " + " AND ".join(condiciones)) if condiciones else ""

        # --- Tendencia mensual: últimos 12 meses ---
        hoy = date.today()
        meses = []
        for i in range(11, -1, -1):
            d = hoy.replace(day=1)
            mes_offset = d.month - i
            anio = d.year + (mes_offset - 1) // 12
            mes = ((mes_offset - 1) % 12) + 1
            meses.append(date(anio, mes, 1))
        tendencia_labels = [m.strftime("%b %Y") for m in meses]
        tendencia_values = []
        for m in meses:
            siguiente = date(m.year + (1 if m.month == 12 else 0), (m.month % 12) + 1, 1)
            cur.execute(
                f"SELECT COUNT(*) as cnt FROM radicados {where} {'AND' if where else 'WHERE'} fecha_radicacion >= ? AND fecha_radicacion < ?",
                params_base + [m.isoformat(), siguiente.isoformat()]
            )
            tendencia_values.append(cur.fetchone()['cnt'])

        # --- Por tipo ---
        cur.execute(f"SELECT tipo_radicado, COUNT(*) as cnt FROM radicados {where} GROUP BY tipo_radicado ORDER BY cnt DESC", params_base)
        tipo_rows = cur.fetchall()

        # --- Por dependencia (top 8) ---
        cur.execute(f"""SELECT COALESCE(NULLIF(seccion_responsable,''), 'Sin asignar') as dep,
                        COUNT(*) as cnt FROM radicados {where}
                        GROUP BY dep ORDER BY cnt DESC LIMIT 8""", params_base)
        dep_rows = cur.fetchall()

        # --- ANS por dependencia ---
        from datetime import date as _date
        _hoy_inf = _date.today().isoformat()
        cur.execute(f"""SELECT COALESCE(NULLIF(seccion_responsable,''), 'Sin asignar') as dep,
                        COUNT(*) as total,
                        SUM(CASE WHEN (fecha_vencimiento IS NULL OR fecha_vencimiento >= ?)
                                 OR estado IN ('Archivado','En Archivo Central') THEN 1 ELSE 0 END) as a_tiempo
                        FROM radicados {where}
                        GROUP BY dep ORDER BY total DESC LIMIT 8""", [_hoy_inf] + params_base)
        ans_dep_rows = cur.fetchall()
        ans_dep_labels = [r['dep'] for r in ans_dep_rows]
        ans_dep_pct = [
            round(r['a_tiempo'] / r['total'] * 100, 1) if r['total'] > 0 else 100.0
            for r in ans_dep_rows
        ]

        # --- Tabla resumen para exportar (máx 500 registros) ---
        cur.execute(f"""SELECT nro_radicado, tipo_radicado, nombre_razon_social, asunto,
                        serie, seccion_responsable, estado, fecha_radicacion, fecha_vencimiento
                        FROM radicados {where} ORDER BY fecha_radicacion DESC LIMIT 500""", params_base)
        resumen = [dict(r) for r in cur.fetchall()]

        return {
            "tendencia": {"labels": tendencia_labels, "values": tendencia_values},
            "por_tipo": {"labels": [r['tipo_radicado'] for r in tipo_rows], "values": [r['cnt'] for r in tipo_rows]},
            "por_dependencia": {"labels": [r['dep'] for r in dep_rows], "values": [r['cnt'] for r in dep_rows]},
            "ans_dependencia": {"labels": ans_dep_labels, "values": ans_dep_pct},
            "resumen": resumen
        }
    finally:
        cur.close()
        conn.close()


@router.get("/eventos-recientes")
async def obtener_eventos_recientes(admin_info: dict = Depends(obtener_admin_actual)):
    """Últimos 15 eventos para el dashboard — acceso rápido sin filtros."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT a.fecha_accion, a.accion, a.modulo, a.detalle, u.usuario
        FROM auditoria a LEFT JOIN usuarios u ON a.usuario_id = u.id
        ORDER BY a.fecha_accion DESC LIMIT 15
    """)
    eventos = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(e) for e in eventos]


@router.get("/audit-logs")
async def obtener_audit_logs(
    admin_info: dict = Depends(obtener_admin_actual),
    usuario: Optional[str] = Query(None, description="Filtrar por nombre de usuario"),
    fecha_desde: Optional[str] = Query(None, description="Fecha inicio YYYY-MM-DD"),
    fecha_hasta: Optional[str] = Query(None, description="Fecha fin YYYY-MM-DD"),
    modulo: Optional[str] = Query(None, description="AUTH | ADMIN | VENTANILLA | ARCHIVO | NOTIFICACIONES"),
    accion: Optional[str] = Query(None, description="Texto parcial de la acción"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200)
):
    """
    Logs de auditoría con filtros y paginación.
    Solo accesible para administradores.
    Los registros son inmutables — solo lectura.
    """
    return consultar_logs(usuario, fecha_desde, fecha_hasta, modulo, accion, page, per_page)


@router.get("/audit-logs/export")
async def exportar_audit_logs(
    admin_info: dict = Depends(obtener_admin_actual),
    usuario: Optional[str] = Query(None),
    fecha_desde: Optional[str] = Query(None),
    fecha_hasta: Optional[str] = Query(None),
    modulo: Optional[str] = Query(None),
    accion: Optional[str] = Query(None)
):
    """
    Exporta logs de auditoría a CSV.
    El archivo incluye todos los registros que coincidan con los filtros.
    """
    from datetime import datetime
    csv_content = exportar_logs_csv(usuario, fecha_desde, fecha_hasta, modulo, accion)
    fecha_export = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"auditoria_siade_{fecha_export}.csv"

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


# ── T8.2 / T8.3 — Editor BPMN: CRUD de plantillas de flujo ──────────────────

TIPOS_FLUJO = ["entrada", "salida", "interna", "archivo"]

@router.get("/workflows")
async def listar_workflows(admin_info: dict = Depends(obtener_admin_actual)):
    """Lista todas las plantillas BPMN guardadas."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, nombre, descripcion, tipo, version, activo, es_default, creado_en, modificado_en
            FROM workflow_templates ORDER BY tipo, version DESC
        """)
        rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        cur.close()
        conn.close()


@router.get("/workflows/{workflow_id}")
async def obtener_workflow(workflow_id: int, admin_info: dict = Depends(obtener_admin_actual)):
    """Obtiene una plantilla BPMN con su XML completo."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM workflow_templates WHERE id = ?", (workflow_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Plantilla no encontrada")
        return dict(row)
    finally:
        cur.close()
        conn.close()


@router.post("/workflows")
async def crear_workflow(
    request: Request,
    admin_info: dict = Depends(obtener_admin_actual)
):
    """Crea una nueva plantilla BPMN."""
    body = await request.json()
    nombre = body.get("nombre", "").strip()
    tipo = body.get("tipo", "").strip()
    xml_content = body.get("xml_content", "").strip()
    descripcion = body.get("descripcion", "").strip()

    if not nombre or not tipo or not xml_content:
        raise HTTPException(status_code=400, detail="nombre, tipo y xml_content son requeridos")
    if tipo not in TIPOS_FLUJO:
        raise HTTPException(status_code=400, detail=f"tipo debe ser uno de: {TIPOS_FLUJO}")

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO workflow_templates (nombre, descripcion, tipo, xml_content, creado_por)
            VALUES (?, ?, ?, ?, ?)
        """, (nombre, descripcion, tipo, xml_content, admin_info['id']))
        conn.commit()
        new_id = cur.lastrowid
        registrar_evento(admin_info['id'], 'CREATE_WORKFLOW', 'ADMIN', f"Plantilla: {nombre}", request)
        return {"id": new_id, "mensaje": "Plantilla creada exitosamente"}
    finally:
        cur.close()
        conn.close()


@router.put("/workflows/{workflow_id}")
async def actualizar_workflow(
    workflow_id: int,
    request: Request,
    admin_info: dict = Depends(obtener_admin_actual)
):
    """Actualiza el XML y metadatos de una plantilla existente."""
    body = await request.json()
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, version FROM workflow_templates WHERE id = ?", (workflow_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Plantilla no encontrada")

        nueva_version = row['version'] + 1
        campos = []
        valores = []
        for campo in ['nombre', 'descripcion', 'xml_content', 'activo']:
            if campo in body:
                campos.append(f"{campo} = ?")
                valores.append(body[campo])

        campos.append("version = ?")
        valores.append(nueva_version)
        campos.append("modificado_en = CURRENT_TIMESTAMP")
        valores.append(workflow_id)

        cur.execute(f"UPDATE workflow_templates SET {', '.join(campos)} WHERE id = ?", valores)
        conn.commit()
        registrar_evento(admin_info['id'], 'UPDATE_WORKFLOW', 'ADMIN', f"ID {workflow_id} v{nueva_version}", request)
        return {"mensaje": "Plantilla actualizada", "version": nueva_version}
    finally:
        cur.close()
        conn.close()


@router.delete("/workflows/{workflow_id}")
async def eliminar_workflow(
    workflow_id: int,
    request: Request,
    admin_info: dict = Depends(obtener_admin_actual)
):
    """Elimina una plantilla (solo si no es default)."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT es_default, nombre FROM workflow_templates WHERE id = ?", (workflow_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Plantilla no encontrada")
        if row['es_default']:
            raise HTTPException(status_code=403, detail="No se pueden eliminar las plantillas predeterminadas")
        cur.execute("DELETE FROM workflow_templates WHERE id = ?", (workflow_id,))
        conn.commit()
        registrar_evento(admin_info['id'], 'DELETE_WORKFLOW', 'ADMIN', f"Eliminada: {row['nombre']}", request)
        return {"mensaje": "Plantilla eliminada"}
    finally:
        cur.close()
        conn.close()
