from typing import Optional
from pydantic import BaseModel


class RadicadoMetadata(BaseModel):
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
