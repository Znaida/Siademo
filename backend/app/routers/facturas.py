"""
T4.5.1 / T4.5.2 — Facturas Electrónicas DIAN
Endpoints para parsear, previsualizar y radicar automáticamente facturas XML UBL 2.1.
No requiere API externa — procesamiento completamente local.
"""
import hashlib
import json
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Depends, Query
from app.core.database import get_db_connection
from app.core.security import obtener_usuario_actual, registrar_evento, generar_consecutivo
from app.core.config import UPLOAD_DIR

router = APIRouter()


@router.post("/facturas/parsear-xml")
async def parsear_xml_dian(
    archivo: UploadFile = File(...),
    user_info: dict = Depends(obtener_usuario_actual)
):
    """Parsea un XML de factura DIAN UBL 2.1 y retorna los datos extraídos para previsualización."""
    if not archivo.filename.lower().endswith('.xml'):
        raise HTTPException(status_code=400, detail="El archivo debe ser un XML de factura electrónica DIAN")

    contenido = await archivo.read()
    try:
        from app.core.dian_parser import parsear_factura_dian, validar_xml_dian
        validacion = validar_xml_dian(contenido)
        datos = parsear_factura_dian(contenido)
        return {"validacion": validacion, "datos": datos}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar el XML: {str(e)}")


@router.post("/facturas/radicar-dian")
async def radicar_desde_dian(
    request: Request,
    archivo: UploadFile = File(...),
    user_info: dict = Depends(obtener_usuario_actual)
):
    """Parsea el XML DIAN y crea automáticamente un radicado de entrada con los datos extraídos."""
    if not archivo.filename.lower().endswith('.xml'):
        raise HTTPException(status_code=400, detail="El archivo debe ser un XML de factura electrónica DIAN")

    contenido = await archivo.read()
    try:
        from app.core.dian_parser import parsear_factura_dian, validar_xml_dian
        validacion = validar_xml_dian(contenido)
        if not validacion["valido"]:
            raise HTTPException(status_code=422, detail=f"XML inválido: {'; '.join(validacion['errores'])}")
        datos = parsear_factura_dian(contenido)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar el XML: {str(e)}")

    # Generar número de radicado
    nro_radicado = generar_consecutivo("RAD")

    # Guardar el XML como archivo principal
    path_xml = f"{UPLOAD_DIR}/{nro_radicado}_principal.xml"
    with open(path_xml, "wb") as f:
        f.write(contenido)
    hash_sha256 = hashlib.sha256(contenido).hexdigest()

    # Calcular fecha de vencimiento (30 días hábiles por defecto para facturas)
    fecha_vencimiento = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    fecha_radicacion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Insertar radicado
        cur.execute("""
            INSERT INTO radicados (
                nro_radicado, tipo_radicado, tipo_remitente, nombre_razon_social,
                tipo_documento, nro_documento, correo_electronico, ciudad,
                departamento, pais, serie, subserie, tipo_documental, asunto,
                metodo_recepcion, nro_folios, dias_respuesta, fecha_vencimiento,
                fecha_radicacion, seccion_responsable, funcionario_responsable_id,
                path_principal, anexos_json, creado_por, estado, hash_sha256
            ) VALUES (
                ?, 'RECIBIDA', 'PERSONA_JURÍDICA', ?,
                'NIT', ?, ?, ?,
                ?, 'Colombia', ?, ?, ?, ?,
                'Correo Electrónico', 1, 30, ?,
                ?, ?, ?,
                ?, ?, ?, 'Radicado', ?
            )
        """, (
            nro_radicado, datos.get("nombre_proveedor", "Proveedor DIAN"),
            datos.get("nit_proveedor", ""), datos.get("correo_proveedor", ""),
            datos.get("ciudad_proveedor", "N/A"),
            datos.get("ciudad_proveedor", "N/A"),
            datos.get("serie_sugerida", "Gestión Financiera"),
            datos.get("subserie_sugerida", "Facturas de Proveedores"),
            datos.get("tipo_documento", "Factura Electrónica"),
            datos.get("asunto_radicacion", f"Factura {datos.get('nro_factura','')}"),
            fecha_vencimiento, fecha_radicacion,
            "Área Financiera", user_info["id"],
            path_xml, "[]", user_info["id"], hash_sha256
        ))

        # Registrar trazabilidad
        cur.execute("""
            INSERT INTO trazabilidad_radicados
                (nro_radicado, accion, comentario, desde_usuario_id, hacia_usuario_id, estado_nuevo)
            VALUES (?, 'CREACION', 'Radicación automática desde XML DIAN.', ?, ?, 'Radicado')
        """, (nro_radicado, user_info["id"], user_info["id"]))

        # Guardar metadatos DIAN en tabla dedicada
        cur.execute("""
            INSERT INTO facturas_dian (
                nro_radicado, tipo_documento, nro_factura, cufe,
                fecha_emision, nit_proveedor, nombre_proveedor,
                ciudad_proveedor, correo_proveedor, valor_bruto,
                descuentos, iva, valor_a_pagar, moneda,
                forma_pago, fecha_vence_pago, asunto_radicacion, estado
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'radicada')
        """, (
            nro_radicado, datos.get("tipo_documento"), datos.get("nro_factura"),
            datos.get("cufe"), datos.get("fecha_emision"),
            datos.get("nit_proveedor"), datos.get("nombre_proveedor"),
            datos.get("ciudad_proveedor"), datos.get("correo_proveedor"),
            datos.get("valor_bruto"), datos.get("descuentos"),
            datos.get("iva"), datos.get("valor_a_pagar"),
            datos.get("moneda", "COP"), datos.get("forma_pago"),
            datos.get("fecha_vence_pago"),
            datos.get("asunto_radicacion")
        ))

        conn.commit()
    finally:
        cur.close()
        conn.close()

    registrar_evento(user_info["id"], "RADICACION_DIAN", "VENTANILLA",
                     f"Factura DIAN {datos.get('nro_factura')} → {nro_radicado}", request)

    return {
        "nro_radicado": nro_radicado,
        "nro_factura": datos.get("nro_factura"),
        "proveedor": datos.get("nombre_proveedor"),
        "valor_a_pagar": datos.get("valor_a_pagar"),
        "fecha_vencimiento": fecha_vencimiento
    }


@router.get("/facturas/dian")
async def listar_facturas_dian(
    q: str = Query(None),
    user_info: dict = Depends(obtener_usuario_actual)
):
    """Lista todas las facturas electrónicas DIAN radicadas."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        if q:
            cur.execute("""
                SELECT f.*, r.estado as estado_radicado
                FROM facturas_dian f
                LEFT JOIN radicados r ON r.nro_radicado = f.nro_radicado
                WHERE f.nro_factura LIKE ? OR f.nombre_proveedor LIKE ? OR f.nit_proveedor LIKE ?
                ORDER BY f.id DESC
            """, (f"%{q}%", f"%{q}%", f"%{q}%"))
        else:
            cur.execute("""
                SELECT f.*, r.estado as estado_radicado
                FROM facturas_dian f
                LEFT JOIN radicados r ON r.nro_radicado = f.nro_radicado
                ORDER BY f.id DESC
            """)
        rows = cur.fetchall()
        facturas = [dict(row) for row in rows]
        return {"facturas": facturas}
    finally:
        cur.close()
        conn.close()


@router.get("/facturas/dian/{factura_id}")
async def detalle_factura_dian(
    factura_id: int,
    user_info: dict = Depends(obtener_usuario_actual)
):
    """Retorna el detalle completo de una factura DIAN."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM facturas_dian WHERE id = ?", (factura_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Factura no encontrada")
        return dict(row)
    finally:
        cur.close()
        conn.close()
