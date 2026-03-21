import os
from passlib.context import CryptContext
from dotenv import load_dotenv

load_dotenv()

# --- Seguridad ---
SECRET_KEY = os.getenv("SECRET_KEY", "dev_local_key_cambiar_en_produccion_2026")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- Almacenamiento ---
if os.getenv("WEBSITE_HOSTNAME"):
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
