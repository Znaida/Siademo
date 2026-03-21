from typing import List, Optional
from pydantic import BaseModel


class DependenciaCreate(BaseModel):
    entidad: str
    unidad_administrativa: str
    oficina_productora: str
    relacion_jerarquica: Optional[str] = "Nivel Raíz"


class TRDCreate(BaseModel):
    cod_unidad: str
    unidad: str
    cod_oficina: str
    oficina: str
    cod_serie: str
    nombre_serie: str
    cod_subserie: Optional[str] = None
    nombre_subserie: Optional[str] = None
    tipo_documental: str
    soporte: str
    extension: str
    años_gestion: int
    años_central: int
    disposicion_final: str
    porcentaje_seleccion: int
    procedimiento: str


class EquipoCreate(BaseModel):
    nombre: str


class AsignacionEquipos(BaseModel):
    usuario_id: int
    equipos_ids: List[int]
