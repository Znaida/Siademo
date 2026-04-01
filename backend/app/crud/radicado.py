"""
CRUD — Radicados
Toda la lógica de acceso a BD para radicados vive aquí.
Los routers llaman estas funciones; no tocan la BD directamente.
"""
import json
import uuid as _uuid
from datetime import datetime, timedelta, date
from fastapi import HTTPException
from app.core.database import get_db_connection
from app.schemas.radicado import RadicadoCreate, TrasladoData, ArchivarData


def crear_radicado(
    data: RadicadoCreate,
    nro_radicado: str,
    path_principal: str,
    rutas_anexos: list,
    creado_por: int,
    hash_sha256: str = ""
) -> dict:
    vencimiento = datetime.now() + timedelta(days=data.dias_respuesta)
    fecha_radicacion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO radicados (
                nro_radicado, tipo_radicado, tipo_remitente, primer_apellido, segundo_apellido,
                nombre_razon_social, tipo_documento, nro_documento, cargo, direccion,
                telefono, correo_electronico, pais, departamento, ciudad,
                serie, subserie, tipo_documental, asunto, metodo_recepcion,
                nro_guia, nro_folios, dias_respuesta, fecha_vencimiento, fecha_radicacion,
                anexo_nombre, descripcion_anexo, seccion_responsable, funcionario_responsable_id,
                con_copia, seccion_origen, funcionario_origen_id,
                nro_radicado_relacionado, path_principal, anexos_json, creado_por, estado, hash_sha256
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
        """, (
            nro_radicado, data.tipo_radicado, data.tipo_remitente,
            data.primer_apellido, data.segundo_apellido, data.nombre_razon_social,
            data.tipo_documento, data.nro_documento, data.cargo, data.direccion,
            data.telefono, data.correo_electronico, data.pais, data.departamento, data.ciudad,
            data.serie, data.subserie, data.tipo_documental, data.asunto, data.metodo_recepcion,
            data.nro_guia, data.nro_folios, data.dias_respuesta,
            str(vencimiento.date()), fecha_radicacion,
            data.anexo_nombre, data.descripcion_anexo, data.seccion_responsable,
            data.funcionario_responsable_id, data.con_copia, data.seccion_origen,
            data.funcionario_origen_id, data.nro_radicado_relacionado,
            path_principal, json.dumps(rutas_anexos), creado_por, 'Radicado', hash_sha256
        ))

        cur.execute("""
            INSERT INTO trazabilidad_radicados
                (nro_radicado, accion, comentario, desde_usuario_id, hacia_usuario_id, estado_nuevo)
            VALUES (?, 'CREACION', 'Radicado creado en ventanilla.', ?, ?, 'Radicado')
        """, (nro_radicado, creado_por, data.funcionario_responsable_id))

        if data.funcionario_responsable_id and data.funcionario_responsable_id != creado_por:
            cur.execute(
                "INSERT INTO notificaciones (usuario_id, nro_radicado, mensaje) VALUES (?, ?, ?)",
                (data.funcionario_responsable_id, nro_radicado,
                 f"Nuevo documento asignado a tu responsabilidad: {nro_radicado}")
            )

        conn.commit()
        return {"nro_radicado": nro_radicado, "vencimiento": str(vencimiento.date())}
    except Exception as e:
        conn.rollback()
        ref = str(_uuid.uuid4())[:8].upper()
        print(f"[ERROR {ref}] {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor. Referencia: {ref}")
    finally:
        cur.close()
        conn.close()


def listar_radicados(
    user_id: int,
    rol: int,
    fecha_desde: str = None,
    fecha_hasta: str = None,
    tipo_doc: str = None,
    estado: str = None,
    dependencia: str = None,
    q: str = None,
    serie_filtro: str = None,
    vencido: str = None,
    page: int = 1,
    per_page: int = 50
) -> dict:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        base_select = """
            SELECT r.nro_radicado, r.tipo_radicado, r.tipo_remitente, r.nombre_razon_social,
                   r.asunto, r.metodo_recepcion, r.serie, r.subserie, r.seccion_responsable,
                   r.fecha_vencimiento, r.fecha_radicacion, r.nro_folios, r.creado_por,
                   r.path_principal, r.estado, r.funcionario_responsable_id,
                   r.nro_radicado_relacionado, r.hash_sha256,
                   (SELECT nro_radicado FROM radicados r2
                    WHERE r2.nro_radicado_relacionado = r.nro_radicado LIMIT 1) AS nro_respuesta,
                   u.nombre_completo AS responsable_nombre, r.id
            FROM radicados r
            LEFT JOIN usuarios u ON r.funcionario_responsable_id = u.id
        """

        condiciones = []
        params = []

        # Filtro por rol
        if rol > 1:
            condiciones.append("(r.creado_por = ? OR r.funcionario_responsable_id = ?)")
            params.extend([user_id, user_id])

        # Filtros opcionales
        if fecha_desde:
            condiciones.append("r.fecha_radicacion >= ?")
            params.append(fecha_desde)
        if fecha_hasta:
            condiciones.append("r.fecha_radicacion <= ?")
            params.append(fecha_hasta + " 23:59:59")
        if tipo_doc:
            condiciones.append("r.tipo_radicado = ?")
            params.append(tipo_doc)
        if estado:
            condiciones.append("r.estado = ?")
            params.append(estado)
        if dependencia:
            condiciones.append("r.seccion_responsable LIKE ?")
            params.append(f"%{dependencia}%")
        if q:
            condiciones.append(
                "(r.nro_radicado LIKE ? OR r.nombre_razon_social LIKE ? OR r.asunto LIKE ? "
                "OR r.serie LIKE ? OR u.nombre_completo LIKE ?)"
            )
            params.extend([f"%{q}%"] * 5)
        if serie_filtro:
            condiciones.append("r.serie LIKE ?")
            params.append(f"%{serie_filtro}%")
        if vencido == 'si':
            condiciones.append("r.fecha_vencimiento IS NOT NULL AND r.fecha_vencimiento < ?")
            params.append(date.today().isoformat())
        elif vencido == 'no':
            condiciones.append("(r.fecha_vencimiento IS NULL OR r.fecha_vencimiento >= ?)")
            params.append(date.today().isoformat())

        where = ("WHERE " + " AND ".join(condiciones)) if condiciones else ""

        # Total de registros (incluir JOIN para que las condiciones con u.nombre_completo funcionen)
        cur.execute(f"SELECT COUNT(*) as cnt FROM radicados r LEFT JOIN usuarios u ON r.funcionario_responsable_id = u.id {where}", params)
        total = cur.fetchone()['cnt']

        # Paginación
        offset = (page - 1) * per_page
        query = f"{base_select} {where} ORDER BY r.id DESC LIMIT ? OFFSET ?"
        cur.execute(query, params + [per_page, offset])

        items = [dict(r) for r in cur.fetchall()]
        return {
            "items": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": max(1, -(-total // per_page))  # ceil division
        }
    finally:
        cur.close()
        conn.close()


def get_path_documento(nro_radicado: str, user_id: int, rol: int) -> str:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        if rol <= 1:
            cur.execute(
                "SELECT path_principal FROM radicados WHERE nro_radicado = ?",
                (nro_radicado,)
            )
        else:
            cur.execute("""
                SELECT path_principal FROM radicados
                WHERE nro_radicado = ? AND (creado_por = ? OR funcionario_responsable_id = ?)
            """, (nro_radicado, user_id, user_id))
        row = cur.fetchone()
        return row['path_principal'] if row else None
    finally:
        cur.close()
        conn.close()


def trasladar_radicado(nro_radicado: str, data: TrasladoData, user_id: int, rol: int) -> dict:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT funcionario_responsable_id, estado FROM radicados WHERE nro_radicado = ?",
            (nro_radicado,)
        )
        rad = cur.fetchone()
        if not rad:
            raise HTTPException(status_code=404, detail="Radicado no encontrado.")
        if rol > 1 and rad['funcionario_responsable_id'] != user_id:
            raise HTTPException(status_code=403, detail="Solo el responsable actual puede trasladar.")

        cur.execute(
            "SELECT id, nombre_completo FROM usuarios WHERE id = ? AND activo = 1",
            (data.nuevo_responsable_id,)
        )
        nuevo_resp = cur.fetchone()
        if not nuevo_resp:
            raise HTTPException(status_code=404, detail="El funcionario destino no existe o está inactivo.")

        cur.execute(
            "UPDATE radicados SET funcionario_responsable_id = ?, estado = 'En Trámite' WHERE nro_radicado = ?",
            (data.nuevo_responsable_id, nro_radicado)
        )
        cur.execute("""
            INSERT INTO trazabilidad_radicados
                (nro_radicado, accion, comentario, desde_usuario_id, hacia_usuario_id, estado_nuevo)
            VALUES (?, 'TRASLADO', ?, ?, ?, 'En Trámite')
        """, (nro_radicado, data.comentario or "Sin comentario.", user_id, data.nuevo_responsable_id))
        cur.execute(
            "INSERT INTO notificaciones (usuario_id, nro_radicado, mensaje) VALUES (?, ?, ?)",
            (data.nuevo_responsable_id, nro_radicado,
             f"Documento trasladado a tu responsabilidad: {nro_radicado}")
        )
        conn.commit()
        return {"mensaje": f"Trasladado a {nuevo_resp['nombre_completo']}."}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        ref = str(_uuid.uuid4())[:8].upper()
        print(f"[ERROR {ref}] {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor. Referencia: {ref}")
    finally:
        cur.close()
        conn.close()


def archivar_radicado(nro_radicado: str, data: ArchivarData, user_id: int, rol: int) -> dict:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT funcionario_responsable_id FROM radicados WHERE nro_radicado = ?",
            (nro_radicado,)
        )
        rad = cur.fetchone()
        if not rad:
            raise HTTPException(status_code=404, detail="Radicado no encontrado.")
        if rol > 1 and rad['funcionario_responsable_id'] != user_id:
            raise HTTPException(status_code=403, detail="Solo el responsable puede archivar.")

        cur.execute(
            "UPDATE radicados SET estado = 'Archivado' WHERE nro_radicado = ?",
            (nro_radicado,)
        )
        cur.execute("""
            INSERT INTO trazabilidad_radicados
                (nro_radicado, accion, comentario, desde_usuario_id, hacia_usuario_id, estado_nuevo)
            VALUES (?, 'ARCHIVADO', ?, ?, NULL, 'Archivado')
        """, (nro_radicado, data.comentario or "Radicado archivado y finalizado.", user_id))
        conn.commit()
        return {"mensaje": "Radicado archivado correctamente."}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        ref = str(_uuid.uuid4())[:8].upper()
        print(f"[ERROR {ref}] {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor. Referencia: {ref}")
    finally:
        cur.close()
        conn.close()


def historial_radicado(nro_radicado: str) -> list:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT t.id, t.accion, t.comentario, t.estado_nuevo, t.fecha,
                   ud.nombre_completo AS desde_nombre, ud.usuario AS desde_usuario,
                   uh.nombre_completo AS hacia_nombre, uh.usuario AS hacia_usuario
            FROM trazabilidad_radicados t
            LEFT JOIN usuarios ud ON t.desde_usuario_id = ud.id
            LEFT JOIN usuarios uh ON t.hacia_usuario_id = uh.id
            WHERE t.nro_radicado = ?
            ORDER BY t.fecha ASC
        """, (nro_radicado,))
        return [dict(r) for r in cur.fetchall()]
    finally:
        cur.close()
        conn.close()
