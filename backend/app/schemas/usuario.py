from pydantic import BaseModel


class UserCreate(BaseModel):
    usuario: str
    password: str
    nombre_completo: str
    rol_id: int


class UserStatusUpdate(BaseModel):
    user_id: int
    nuevo_estado: bool
