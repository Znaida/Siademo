import os
import json
import hashlib
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form, Depends, Query
from fastapi.responses import FileResponse
from app.core.config import UPLOAD_DIR
from app.core.database import get_db_connection
from app.core.security import obtener_usuario_actual, registrar_evento, generar_consecutivo
from app.schemas.radicado import RadicadoCreate, TrasladoData, ArchivarData
from app.crud.radicado import (
    crear_radicado, listar_radicados, get_path_documento,
    trasladar_radicado, archivar_radicado, historial_radicado
)

# Mapa de estados → paso BPMN actual y pasos completados por tipo de radicado
FLUJO_MAP = {
    "RAD": {  # Comunicaciones recibidas
        "archivo": "radicacion-entrada.bpmn",
        "pasos": ["inicio", "ventanillaRadica", "generarSticker", "documentoCompleto",
                  "asignarDependencia", "dependenciaRevisa", "requiereRespuesta",
                  "elaborarRespuesta", "notificarCiudadano", "archivarDocumento", "finProceso"],
        "estados": {
            "Radicado":    {"actual": "asignarDependencia",   "completados": ["ventanillaRadica", "generarSticker"]},
            "Asignado":    {"actual": "dependenciaRevisa",    "completados": ["ventanillaRadica", "generarSticker", "asignarDependencia"]},
            "En trámite":  {"actual": "dependenciaRevisa",    "completados": ["ventanillaRadica", "generarSticker", "asignarDependencia"]},
            "Respondido":  {"actual": "notificarCiudadano",   "completados": ["ventanillaRadica", "generarSticker", "asignarDependencia", "dependenciaRevisa", "elaborarRespuesta"]},
            "Archivado":   {"actual": "finProceso",           "completados": ["ventanillaRadica", "generarSticker", "asignarDependencia", "dependenciaRevisa", "elaborarRespuesta", "notificarCiudadano", "archivarDocumento"]},
        }
    },
    "ENV": {  # Comunicaciones enviadas
        "archivo": "radicacion-salida.bpmn",
        "pasos": ["inicio", "jefeAprueba", "aprobado", "ventanillaRadica", "generarSticker",
                  "medioEnvio", "enviarCorreo", "enviarFisico", "archivar", "fin"],
        "estados": {
            "Radicado":    {"actual": "ventanillaRadica",     "completados": ["jefeAprueba"]},
            "Asignado":    {"actual": "generarSticker",       "completados": ["jefeAprueba", "ventanillaRadica"]},
            "En trámite":  {"actual": "medioEnvio",           "completados": ["jefeAprueba", "ventanillaRadica", "generarSticker"]},
            "Respondido":  {"actual": "archivar",             "completados": ["jefeAprueba", "ventanillaRadica", "generarSticker", "enviarCorreo"]},
            "Archivado":   {"actual": "fin",                  "completados": ["jefeAprueba", "ventanillaRadica", "generarSticker", "enviarCorreo", "archivar"]},
        }
    },
    "INV": {  # Comunicaciones internas
        "archivo": "comunicacion-interna.bpmn",
        "pasos": ["inicio", "redactarMemorando", "jefeAprueba", "aprobado", "radicarInterno",
                  "notificarDestinatario", "destinatarioRecibe", "requiereAccion", "ejecutarAccion", "archivar", "fin"],
        "estados": {
            "Radicado":    {"actual": "notificarDestinatario", "completados": ["redactarMemorando", "jefeAprueba", "radicarInterno"]},
            "Asignado":    {"actual": "destinatarioRecibe",    "completados": ["redactarMemorando", "jefeAprueba", "radicarInterno", "notificarDestinatario"]},
            "En trámite":  {"actual": "ejecutarAccion",        "completados": ["redactarMemorando", "jefeAprueba", "radicarInterno", "notificarDestinatario", "destinatarioRecibe"]},
            "Respondido":  {"actual": "archivar",              "completados": ["redactarMemorando", "jefeAprueba", "radicarInterno", "notificarDestinatario", "destinatarioRecibe", "ejecutarAccion"]},
            "Archivado":   {"actual": "fin",                   "completados": ["redactarMemorando", "jefeAprueba", "radicarInterno", "notificarDestinatario", "destinatarioRecibe", "ejecutarAccion", "archivar"]},
        }
    },
    "NOR": {  # No radicables
        "archivo": "radicacion-entrada.bpmn",
        "pasos": ["inicio", "ventanillaRadica"],
        "estados": {
            "Radicado":    {"actual": "ventanillaRadica", "completados": ["inicio"]},
            "Archivado":   {"actual": "finDevolucion",    "completados": ["ventanillaRadica", "devolverCiudadano"]},
        }
    }
}

router = APIRouter()


@router.post("/radicar")
async def radicar_oficial(
    request: Request,
    metadata: str = Form(...),
    archivo_principal: UploadFile = File(...),
    anexos: List[UploadFile] = File(None),
    user_info: dict = Depends(obtener_usuario_actual)
):
    data = RadicadoCreate.model_validate_json(metadata)

    prefix_map = {'RECIBIDA': 'RAD', 'ENVIADA': 'ENV', 'INTERNA': 'INV', 'NO-RADICABLE': 'NOR'}
    prefijo = prefix_map.get(data.tipo_radicado, 'NOR')
    nro_radicado = generar_consecutivo(prefijo)

    # Leer contenido del archivo principal para calcular SHA-256
    contenido_principal = await archivo_principal.read()
    hash_sha256 = hashlib.sha256(contenido_principal).hexdigest()

    ext = archivo_principal.filename.split(".")[-1]
    path_p = f"{UPLOAD_DIR}/{nro_radicado}_principal.{ext}"
    with open(path_p, "wb") as f:
        f.write(contenido_principal)

    rutas_anexos = []
    if anexos:
        for i, anexo in enumerate(anexos):
            contenido_anexo = await anexo.read()
            a_ext = anexo.filename.split(".")[-1]
            path_a = f"{UPLOAD_DIR}/{nro_radicado}_anexo_{i}.{a_ext}"
            with open(path_a, "wb") as f:
                f.write(contenido_anexo)
            rutas_anexos.append(path_a)

    resultado = crear_radicado(data, nro_radicado, path_p, rutas_anexos, user_info['id'], hash_sha256)
    registrar_evento(user_info['id'], 'RADICACION_OFICIAL', 'VENTANILLA',
                     f"Generado: {nro_radicado}", request)
    return {"status": "success", **resultado}


@router.get("/radicados")
async def endpoint_listar_radicados(
    user_info: dict = Depends(obtener_usuario_actual),
    fecha_desde: Optional[str] = Query(None),
    fecha_hasta: Optional[str] = Query(None),
    tipo_doc: Optional[str] = Query(None),
    estado: Optional[str] = Query(None),
    dependencia: Optional[str] = Query(None),
    q: Optional[str] = Query(None, description="Búsqueda libre"),
    serie_filtro: Optional[str] = Query(None, description="Filtro por serie"),
    vencido: Optional[str] = Query(None, description="si | no"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200)
):
    return listar_radicados(
        user_info['id'], user_info['rol'],
        fecha_desde, fecha_hasta, tipo_doc, estado, dependencia,
        q, serie_filtro, vencido, page, per_page
    )


@router.get("/radicados/{nro_radicado}/documento")
async def ver_documento_radicado(
    nro_radicado: str,
    user_info: dict = Depends(obtener_usuario_actual)
):
    path = get_path_documento(nro_radicado, user_info['id'], user_info['rol'])
    if not path:
        raise HTTPException(status_code=404, detail="Documento no encontrado.")

    storage_dir = os.path.realpath(UPLOAD_DIR)
    real_path = os.path.realpath(path)
    if not real_path.startswith(storage_dir):
        raise HTTPException(status_code=403, detail="Acceso al archivo no permitido.")
    if not os.path.exists(real_path):
        raise HTTPException(status_code=404, detail="El archivo ya no existe en el servidor.")

    filename = os.path.basename(real_path)
    media_type = "application/pdf" if filename.endswith(".pdf") else "application/octet-stream"
    return FileResponse(path=real_path, filename=filename, media_type=media_type)


@router.post("/radicados/{nro_radicado}/trasladar")
async def endpoint_trasladar(
    nro_radicado: str,
    data: TrasladoData,
    request: Request,
    user_info: dict = Depends(obtener_usuario_actual)
):
    resultado = trasladar_radicado(nro_radicado, data, user_info['id'], user_info['rol'])
    registrar_evento(user_info['id'], 'TRASLADO', 'GESTION',
                     f"{nro_radicado} → User ID {data.nuevo_responsable_id}", request)
    return {"status": "success", **resultado}


@router.post("/radicados/{nro_radicado}/archivar")
async def endpoint_archivar(
    nro_radicado: str,
    data: ArchivarData,
    request: Request,
    user_info: dict = Depends(obtener_usuario_actual)
):
    resultado = archivar_radicado(nro_radicado, data, user_info['id'], user_info['rol'])
    registrar_evento(user_info['id'], 'ARCHIVADO', 'GESTION', nro_radicado, request)
    return {"status": "success", **resultado}


@router.get("/radicados/{nro_radicado}/historial")
async def endpoint_historial(
    nro_radicado: str,
    user_info: dict = Depends(obtener_usuario_actual)
):
    return historial_radicado(nro_radicado)


@router.post("/radicados/dian/parsear")
async def parsear_xml_dian(
    archivo_xml: UploadFile = File(...),
    user_info: dict = Depends(obtener_usuario_actual)
):
    """T4.5.1 — Parsea factura electrónica DIAN (XML UBL 2.1) y retorna datos para pre-llenar el formulario de radicación."""
    if not archivo_xml.filename.lower().endswith('.xml'):
        raise HTTPException(status_code=400, detail="El archivo debe ser un XML de factura electrónica DIAN")

    contenido = await archivo_xml.read()
    try:
        from app.core.dian_parser import parsear_factura_dian, validar_xml_dian
        validacion = validar_xml_dian(contenido)
        datos = parsear_factura_dian(contenido)
        return {"valido": validacion["valido"], "advertencias": validacion["advertencias"], **datos}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar el XML: {str(e)}")


@router.get("/radicados/{nro_radicado}/flujo")
async def endpoint_flujo(
    nro_radicado: str,
    user_info: dict = Depends(obtener_usuario_actual)
):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT nro_radicado, tipo_radicado, estado FROM radicados WHERE nro_radicado = ?", (nro_radicado,))
    rad = cur.fetchone()
    conn.close()

    if not rad:
        raise HTTPException(status_code=404, detail="Radicado no encontrado")

    # Determinar prefijo del tipo
    prefijo = rad["tipo_radicado"][:3].upper() if rad["tipo_radicado"] else "RAD"
    prefijo_map = {
        "COM": "RAD", "RAD": "RAD", "ENV": "ENV", "INV": "INV", "NOR": "NOR",
        "CAR": "RAD", "DER": "RAD", "PET": "RAD"
    }
    # Intentar extraer prefijo del nro_radicado directamente
    nro_prefijo = nro_radicado.split("-")[0] if "-" in nro_radicado else "RAD"
    flujo_config = FLUJO_MAP.get(nro_prefijo, FLUJO_MAP["RAD"])

    estado = rad["estado"] or "Radicado"
    estado_config = flujo_config["estados"].get(estado, flujo_config["estados"]["Radicado"])

    return {
        "nro_radicado": nro_radicado,
        "estado": estado,
        "archivo_bpmn": flujo_config["archivo"],
        "paso_actual": estado_config["actual"],
        "pasos_completados": estado_config["completados"],
        "todos_los_pasos": flujo_config["pasos"]
    }
