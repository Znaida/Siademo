import os
import json
import shutil
from datetime import datetime, timedelta
from typing import List
from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form, Depends
from fastapi.responses import FileResponse
from app.core.config import UPLOAD_DIR
from app.core.database import get_db_connection
from app.core.security import obtener_usuario_actual, registrar_evento, generar_consecutivo
from app.schemas.radicado import RadicadoMetadata, TrasladoData, ArchivarData

router = APIRouter()


@router.post("/radicar")
async def radicar_oficial(
    request: Request,
    metadata: str = Form(...),
    archivo_principal: UploadFile = File(...),
    anexos: List[UploadFile] = File(None),
    user_info: dict = Depends(obtener_usuario_actual)
):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        data = RadicadoMetadata.parse_raw(metadata)

        prefix_map = {'RECIBIDA': 'RAD', 'ENVIADA': 'ENV', 'INTERNA': 'INV', 'NO-RADICABLE': 'NOR'}
        prefijo = prefix_map.get(data.tipo_radicado, 'NOR')
        nro_radicado = generar_consecutivo(prefijo)

        ext = archivo_principal.filename.split(".")[-1]
        path_p = f"{UPLOAD_DIR}/{nro_radicado}_principal.{ext}"
        with open(path_p, "wb") as buffer:
            shutil.copyfileobj(archivo_principal.file, buffer)

        rutas_anexos = []
        if anexos:
            for i, anexo in enumerate(anexos):
                a_ext = anexo.filename.split(".")[-1]
                path_a = f"{UPLOAD_DIR}/{nro_radicado}_anexo_{i}.{a_ext}"
                with open(path_a, "wb") as buffer:
                    shutil.copyfileobj(anexo.file, buffer)
                rutas_anexos.append(path_a)

        vencimiento = datetime.now() + timedelta(days=data.dias_respuesta)

        cur.execute("""
            INSERT INTO radicados (
                nro_radicado, tipo_radicado, tipo_remitente, primer_apellido, segundo_apellido,
                nombre_razon_social, tipo_documento, nro_documento, cargo, direccion,
                telefono, correo_electronico, pais, departamento, ciudad,
                serie, subserie, tipo_documental, asunto, metodo_recepcion,
                nro_guia, nro_folios, dias_respuesta, fecha_vencimiento, anexo_nombre, descripcion_anexo,
                seccion_responsable, funcionario_responsable_id, con_copia, seccion_origen, funcionario_origen_id,
                path_principal, anexos_json, creado_por, estado
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            nro_radicado, data.tipo_radicado, data.tipo_remitente, data.primer_apellido, data.segundo_apellido,
            data.nombre_razon_social, data.tipo_documento, data.nro_documento, data.cargo, data.direccion,
            data.telefono, data.correo_electronico, data.pais, data.departamento, data.ciudad,
            data.serie, data.subserie, data.tipo_documental, data.asunto, data.metodo_recepcion,
            data.nro_guia, data.nro_folios, data.dias_respuesta, vencimiento.date(), data.anexo_nombre, data.descripcion_anexo,
            data.seccion_responsable, data.funcionario_responsable_id, data.con_copia, data.seccion_origen, data.funcionario_origen_id,
            path_p, json.dumps(rutas_anexos), user_info['id'], 'Radicado'
        ))

        cur.execute("""
            INSERT INTO trazabilidad_radicados (nro_radicado, accion, comentario, desde_usuario_id, hacia_usuario_id, estado_nuevo)
            VALUES (?, 'CREACION', 'Radicado creado en ventanilla.', ?, ?, 'Radicado')
        """, (nro_radicado, user_info['id'], data.funcionario_responsable_id))

        if data.funcionario_responsable_id and data.funcionario_responsable_id != user_info['id']:
            cur.execute(
                "INSERT INTO notificaciones (usuario_id, nro_radicado, mensaje) VALUES (?, ?, ?)",
                (data.funcionario_responsable_id, nro_radicado, f"Nuevo documento recibido: {nro_radicado}")
            )

        conn.commit()
        registrar_evento(user_info['id'], 'RADICACION_OFICIAL', 'VENTANILLA', f"Generado: {nro_radicado}", request)
        return {"status": "success", "numero": nro_radicado, "vencimiento": str(vencimiento.date())}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


@router.get("/radicados")
async def listar_radicados(user_info: dict = Depends(obtener_usuario_actual)):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        es_admin = user_info['rol'] <= 1
        if es_admin:
            cur.execute("""
                SELECT r.nro_radicado, r.tipo_radicado, r.tipo_remitente, r.nombre_razon_social,
                       r.asunto, r.metodo_recepcion, r.serie, r.subserie, r.seccion_responsable,
                       r.fecha_vencimiento, r.nro_folios, r.creado_por, r.path_principal,
                       r.estado, r.funcionario_responsable_id, r.nro_radicado_relacionado,
                       (SELECT nro_radicado FROM radicados r2 WHERE r2.nro_radicado_relacionado = r.nro_radicado LIMIT 1) AS nro_respuesta,
                       u.nombre_completo AS responsable_nombre, r.rowid as id
                FROM radicados r
                LEFT JOIN usuarios u ON r.funcionario_responsable_id = u.id
                ORDER BY r.rowid DESC
            """)
        else:
            cur.execute("""
                SELECT r.nro_radicado, r.tipo_radicado, r.tipo_remitente, r.nombre_razon_social,
                       r.asunto, r.metodo_recepcion, r.serie, r.subserie, r.seccion_responsable,
                       r.fecha_vencimiento, r.nro_folios, r.creado_por, r.path_principal,
                       r.estado, r.funcionario_responsable_id, r.nro_radicado_relacionado,
                       (SELECT nro_radicado FROM radicados r2 WHERE r2.nro_radicado_relacionado = r.nro_radicado LIMIT 1) AS nro_respuesta,
                       u.nombre_completo AS responsable_nombre, r.rowid as id
                FROM radicados r
                LEFT JOIN usuarios u ON r.funcionario_responsable_id = u.id
                WHERE r.creado_por = ? OR r.funcionario_responsable_id = ?
                ORDER BY r.rowid DESC
            """, (user_info['id'], user_info['id']))
        return [dict(r) for r in cur.fetchall()]
    finally:
        cur.close()
        conn.close()


@router.get("/radicados/{nro_radicado}/documento")
async def ver_documento_radicado(nro_radicado: str, user_info: dict = Depends(obtener_usuario_actual)):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        if user_info['rol'] <= 1:
            cur.execute("SELECT path_principal FROM radicados WHERE nro_radicado = ?", (nro_radicado,))
        else:
            cur.execute("""
                SELECT path_principal FROM radicados
                WHERE nro_radicado = ? AND (creado_por = ? OR funcionario_responsable_id = ?)
            """, (nro_radicado, user_info['id'], user_info['id']))
        row = cur.fetchone()
    finally:
        cur.close()
        conn.close()

    if not row or not row['path_principal']:
        raise HTTPException(status_code=404, detail="Documento no encontrado.")

    storage_dir = os.path.realpath(UPLOAD_DIR)
    real_path = os.path.realpath(row['path_principal'])
    if not real_path.startswith(storage_dir):
        raise HTTPException(status_code=403, detail="Acceso al archivo no permitido.")
    if not os.path.exists(real_path):
        raise HTTPException(status_code=404, detail="El archivo ya no existe en el servidor.")

    filename = os.path.basename(real_path)
    media_type = "application/pdf" if filename.endswith(".pdf") else "application/octet-stream"
    return FileResponse(path=real_path, filename=filename, media_type=media_type)


@router.post("/radicados/{nro_radicado}/trasladar")
async def trasladar_radicado(nro_radicado: str, data: TrasladoData, request: Request, user_info: dict = Depends(obtener_usuario_actual)):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT funcionario_responsable_id, estado FROM radicados WHERE nro_radicado = ?", (nro_radicado,))
        rad = cur.fetchone()
        if not rad:
            raise HTTPException(status_code=404, detail="Radicado no encontrado.")
        if user_info['rol'] > 1 and rad['funcionario_responsable_id'] != user_info['id']:
            raise HTTPException(status_code=403, detail="Solo el responsable actual puede trasladar.")

        cur.execute("SELECT id, nombre_completo FROM usuarios WHERE id = ? AND activo = 1", (data.nuevo_responsable_id,))
        nuevo_resp = cur.fetchone()
        if not nuevo_resp:
            raise HTTPException(status_code=404, detail="El funcionario destino no existe o está inactivo.")

        cur.execute("UPDATE radicados SET funcionario_responsable_id = ?, estado = 'En Trámite' WHERE nro_radicado = ?",
                    (data.nuevo_responsable_id, nro_radicado))
        cur.execute("""
            INSERT INTO trazabilidad_radicados (nro_radicado, accion, comentario, desde_usuario_id, hacia_usuario_id, estado_nuevo)
            VALUES (?, 'TRASLADO', ?, ?, ?, 'En Trámite')
        """, (nro_radicado, data.comentario or "Sin comentario.", user_info['id'], data.nuevo_responsable_id))
        cur.execute("INSERT INTO notificaciones (usuario_id, nro_radicado, mensaje) VALUES (?, ?, ?)",
                    (data.nuevo_responsable_id, nro_radicado, f"Documento trasladado a tu responsabilidad: {nro_radicado}"))

        conn.commit()
        registrar_evento(user_info['id'], 'TRASLADO', 'GESTION', f"{nro_radicado} → User ID {data.nuevo_responsable_id}", request)
        return {"status": "success", "mensaje": f"Trasladado a {nuevo_resp['nombre_completo']}."}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


@router.post("/radicados/{nro_radicado}/archivar")
async def archivar_radicado(nro_radicado: str, data: ArchivarData, request: Request, user_info: dict = Depends(obtener_usuario_actual)):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT funcionario_responsable_id FROM radicados WHERE nro_radicado = ?", (nro_radicado,))
        rad = cur.fetchone()
        if not rad:
            raise HTTPException(status_code=404, detail="Radicado no encontrado.")
        if user_info['rol'] > 1 and rad['funcionario_responsable_id'] != user_info['id']:
            raise HTTPException(status_code=403, detail="Solo el responsable puede archivar.")

        cur.execute("UPDATE radicados SET estado = 'Archivado' WHERE nro_radicado = ?", (nro_radicado,))
        cur.execute("""
            INSERT INTO trazabilidad_radicados (nro_radicado, accion, comentario, desde_usuario_id, hacia_usuario_id, estado_nuevo)
            VALUES (?, 'ARCHIVADO', ?, ?, NULL, 'Archivado')
        """, (nro_radicado, data.comentario or "Radicado archivado y finalizado.", user_info['id']))

        conn.commit()
        registrar_evento(user_info['id'], 'ARCHIVADO', 'GESTION', nro_radicado, request)
        return {"status": "success", "mensaje": "Radicado archivado correctamente."}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


@router.get("/radicados/{nro_radicado}/historial")
async def historial_radicado(nro_radicado: str, user_info: dict = Depends(obtener_usuario_actual)):
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
