import datetime
from fastapi import APIRouter, HTTPException, Request, Depends
from app.core.database import get_db_connection
from app.core.security import obtener_usuario_actual, obtener_admin_actual, registrar_evento
from app.schemas.radicado import TransferenciaData

router = APIRouter()


@router.post("/radicados/{nro_radicado}/transferir-archivo")
async def transferir_a_archivo_central(
    nro_radicado: str,
    data: TransferenciaData,
    request: Request,
    user_info: dict = Depends(obtener_admin_actual)
):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM radicados WHERE nro_radicado = ?", (nro_radicado,))
        rad = cur.fetchone()
        if not rad:
            raise HTTPException(status_code=404, detail="Radicado no encontrado.")
        if rad['estado'] != 'Archivado':
            raise HTTPException(status_code=400, detail="Solo se pueden transferir radicados con estado 'Archivado'.")

        cur.execute("SELECT disposicion_final FROM trd WHERE nombre_serie = ? LIMIT 1", (rad['serie'],))
        trd_row = cur.fetchone()
        disposicion = trd_row['disposicion_final'] if trd_row else 'Conservación Total'
        anio = datetime.datetime.now().year

        cur.execute("""
            INSERT OR REPLACE INTO archivo_central
            (nro_radicado, serie, subserie, tipo_documental, asunto, anio_produccion,
             caja, carpeta, folio_inicio, folio_fin, llaves_busqueda, observaciones,
             disposicion_final, path_principal, transferido_por)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (nro_radicado, rad['serie'], rad['subserie'], rad['tipo_documental'], rad['asunto'], anio,
              data.caja, data.carpeta, data.folio_inicio, data.folio_fin,
              data.llaves_busqueda, data.observaciones, disposicion, rad['path_principal'], user_info['id']))

        cur.execute("UPDATE radicados SET estado = 'En Archivo Central' WHERE nro_radicado = ?", (nro_radicado,))
        cur.execute("""
            INSERT INTO trazabilidad_radicados (nro_radicado, accion, comentario, desde_usuario_id, estado_nuevo)
            VALUES (?, 'TRANSFERENCIA', ?, ?, 'En Archivo Central')
        """, (nro_radicado, f"Transferido. Caja: {data.caja}, Carpeta: {data.carpeta}.", user_info['id']))

        conn.commit()
        registrar_evento(user_info['id'], 'TRANSFERENCIA_ARCHIVO', 'ARCHIVO_CENTRAL', nro_radicado, request)
        return {"status": "success", "mensaje": f"Transferido al Archivo Central. Disposición: {disposicion}."}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


@router.get("/archivo-central")
async def consultar_archivo_central(
    q: str = "", anio: int = 0, serie: str = "", caja: str = "",
    disposicion: str = "", user_info: dict = Depends(obtener_usuario_actual)
):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        filtros, params = [], []
        if q:
            filtros.append("(a.nro_radicado LIKE ? OR a.asunto LIKE ? OR a.llaves_busqueda LIKE ?)")
            params += [f"%{q}%", f"%{q}%", f"%{q}%"]
        if anio:
            filtros.append("a.anio_produccion = ?")
            params.append(anio)
        if serie:
            filtros.append("a.serie LIKE ?")
            params.append(f"%{serie}%")
        if caja:
            filtros.append("a.caja LIKE ?")
            params.append(f"%{caja}%")
        if disposicion:
            filtros.append("a.disposicion_final = ?")
            params.append(disposicion)

        where = ("WHERE " + " AND ".join(filtros)) if filtros else ""
        cur.execute(f"""
            SELECT a.*, u.nombre_completo AS transferido_por_nombre
            FROM archivo_central a
            LEFT JOIN usuarios u ON a.transferido_por = u.id
            {where}
            ORDER BY a.fecha_transferencia DESC
        """, params)
        return [dict(r) for r in cur.fetchall()]
    finally:
        cur.close()
        conn.close()
