import os
import os as _os
from passlib.context import CryptContext
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    secret_key: str
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
_is_prod = bool(_os.getenv("WEBSITE_HOSTNAME"))
ALLOWED_ORIGINS = [
    "https://ashy-desert-090fd4a0f.2.azurestaticapps.net",
] + ([] if _is_prod else ["http://localhost:4200", "http://127.0.0.1:4200"])
