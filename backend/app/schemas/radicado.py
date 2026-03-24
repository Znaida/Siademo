from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, field_validator


# ─── Entrada: crear radicado ───────────────────────────────────────────────
class RadicadoCreate(BaseModel):
    tipo_radicado: str
    tipo_remitente: str
    primer_apellido: Optional[str] = None
    segundo_apellido: Optional[str] = None
    nombre_razon_social: str
    tipo_documento: str
    nro_documento: str
    cargo: Optional[str] = None
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    correo_electronico: Optional[str] = None
    pais: str = "Colombia"
    departamento: str
    ciudad: str
    serie: str
    subserie: str
    tipo_documental: str
    asunto: str
    metodo_recepcion: str
    seccion_origen: Optional[str] = None
    funcionario_origen_id: Optional[int] = None
    nro_guia: Optional[str] = None
    nro_folios: int = 1
    dias_respuesta: int = 15
    anexo_nombre: Optional[str] = None
    descripcion_anexo: Optional[str] = None
    seccion_responsable: str
    funcionario_responsable_id: int
    con_copia: Optional[str] = None
    nro_radicado_relacionado: Optional[str] = None
    activa_flujo_id: Optional[int] = None

    @field_validator("nro_folios")
    @classmethod
    def folios_positivos(cls, v: int) -> int:
        if v < 1:
            raise ValueError("nro_folios debe ser al menos 1")
        return v

    @field_validator("dias_respuesta")
    @classmethod
    def dias_positivos(cls, v: int) -> int:
        if v < 0:
            raise ValueError("dias_respuesta no puede ser negativo")
        return v


# Alias para compatibilidad con código existente
RadicadoMetadata = RadicadoCreate


# ─── Respuesta: lo que devuelve la API ────────────────────────────────────
class RadicadoResponse(BaseModel):
    id: int
    nro_radicado: str
    fecha_radicacion: str
    tipo_radicado: str
    asunto: str
    estado: str
    nombre_razon_social: str
    tipo_remitente: str
    serie: str
    subserie: str
    seccion_responsable: str
    metodo_recepcion: str
    nro_folios: int
    dias_respuesta: int
    funcionario_responsable_id: Optional[int] = None
    nro_radicado_relacionado: Optional[str] = None

    model_config = {"from_attributes": True}


# ─── Trazabilidad ─────────────────────────────────────────────────────────
class TrazabilidadResponse(BaseModel):
    id: int
    nro_radicado: str
    accion: str
    descripcion: Optional[str] = None
    usuario: Optional[str] = None
    fecha: str
    ip: Optional[str] = None

    model_config = {"from_attributes": True}


# ─── Operaciones sobre radicados ──────────────────────────────────────────
class TrasladoData(BaseModel):
    nuevo_responsable_id: int
    comentario: str = ""


class ArchivarData(BaseModel):
    comentario: str = ""


class TransferenciaData(BaseModel):
    caja: str = ""
    carpeta: str = ""
    folio_inicio: Optional[int] = None
    folio_fin: Optional[int] = None
    llaves_busqueda: str = ""
    observaciones: str = ""
