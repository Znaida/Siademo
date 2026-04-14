from typing import List, Optional
from pydantic import BaseModel, field_validator


# ─── Dependencias / Estructura orgánica ───────────────────────────────────
class DependenciaCreate(BaseModel):
    entidad: str
    cod_unidad: str
    unidad_administrativa: str
    cod_oficina: str
    oficina_productora: str


class DependenciaResponse(BaseModel):
    id: int
    entidad: str
    unidad_administrativa: str
    oficina_productora: str
    relacion_jerarquica: Optional[str] = None

    model_config = {"from_attributes": True}


# ─── TRD ──────────────────────────────────────────────────────────────────
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

    @field_validator("años_gestion", "años_central")
    @classmethod
    def anos_positivos(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Los años de retención no pueden ser negativos")
        return v

    @field_validator("porcentaje_seleccion")
    @classmethod
    def porcentaje_valido(cls, v: int) -> int:
        if not (0 <= v <= 100):
            raise ValueError("El porcentaje de selección debe estar entre 0 y 100")
        return v


class TRDResponse(BaseModel):
    id: int
    cod_serie: str
    nombre_serie: str
    cod_subserie: Optional[str] = None
    nombre_subserie: Optional[str] = None
    tipo_documental: str
    años_gestion: int
    años_central: int
    disposicion_final: str

    model_config = {"from_attributes": True}


# ─── Equipos ──────────────────────────────────────────────────────────────
class EquipoCreate(BaseModel):
    nombre: str

    @field_validator("nombre")
    @classmethod
    def nombre_no_vacio(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("El nombre del equipo no puede estar vacío")
        return v.strip()


class EquipoResponse(BaseModel):
    id: int
    nombre: str

    model_config = {"from_attributes": True}


# ─── Asignación de equipos ────────────────────────────────────────────────
class AsignacionEquipos(BaseModel):
    usuario_id: int
    equipos_ids: List[int]
