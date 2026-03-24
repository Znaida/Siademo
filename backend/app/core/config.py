import os
from passlib.context import CryptContext
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    secret_key: str = "dev_local_key_cambiar_en_produccion_2026"
    algorithm: str = "HS256"
    admin_user: str = ""
    admin_pass: str = ""
    admin_name: str = "Administrador de Sistema"
    website_hostname: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()

# --- Seguridad ---
SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- Almacenamiento ---
if settings.website_hostname:
    UPLOAD_DIR = "/home/site/wwwroot/storage"
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    UPLOAD_DIR = os.path.join(BASE_DIR, "..", "storage")

os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- CORS ---
ALLOWED_ORIGINS = [
    "https://ashy-desert-090fd4a0f.2.azurestaticapps.net",
    "http://localhost:4200",
]
