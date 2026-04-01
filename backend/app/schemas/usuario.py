from typing import Optional
from pydantic import BaseModel, field_validator


# ─── Entrada: crear usuario ───────────────────────────────────────────────
class UserCreate(BaseModel):
    usuario: str
    password: str
    nombre_completo: str
    rol_id: int

    @field_validator("usuario")
    @classmethod
    def usuario_sin_espacios(cls, v: str) -> str:
        if " " in v:
            raise ValueError("El nombre de usuario no puede contener espacios")
        return v.lower()

    @field_validator("password")
    @classmethod
    def password_minimo(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        return v

    @field_validator("rol_id")
    @classmethod
    def rol_valido(cls, v: int) -> int:
        if v not in (0, 1, 2, 3):
            raise ValueError("rol_id debe ser 0 (SuperAdmin), 1 (Admin), 2 (Productor) o 3 (Consultor)")
        return v


# ─── Entrada: admin crea usuario (sin contraseña, la genera el sistema) ───
class UserCreateAdmin(BaseModel):
    usuario: str
    nombre_completo: str
    rol_id: int

    @field_validator("usuario")
    @classmethod
    def usuario_sin_espacios(cls, v: str) -> str:
        if " " in v:
            raise ValueError("El nombre de usuario no puede contener espacios")
        return v.lower()

    @field_validator("rol_id")
    @classmethod
    def rol_valido(cls, v: int) -> int:
        if v not in (0, 1, 2, 3):
            raise ValueError("rol_id debe ser 0, 1, 2 o 3")
        return v


# ─── Entrada: cambiar contraseña ──────────────────────────────────────────
class CambiarPasswordData(BaseModel):
    password_actual: str
    password_nuevo: str
    password_confirmar: str

    @field_validator("password_nuevo")
    @classmethod
    def password_minimo(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        if v.isdigit():
            raise ValueError("La contraseña no puede ser solo números")
        if v.isalpha():
            raise ValueError("La contraseña debe incluir al menos un número")
        return v

    def validar_confirmacion(self) -> None:
        if self.password_nuevo != self.password_confirmar:
            raise ValueError("Las contraseñas no coinciden")


# ─── Entrada: cambiar estado ──────────────────────────────────────────────
class UserStatusUpdate(BaseModel):
    user_id: int
    nuevo_estado: bool


# ─── Respuesta: lo que devuelve la API ────────────────────────────────────
class UsuarioResponse(BaseModel):
    id_usuario: int
    usuario: str
    nombre_completo: str
    rol_id: int
    activo: bool

    model_config = {"from_attributes": True}


# ─── InDB: representación interna (incluye hash) ──────────────────────────
class UsuarioInDB(UsuarioResponse):
    password_hash: str

    model_config = {"from_attributes": True}
