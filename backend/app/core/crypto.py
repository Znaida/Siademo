"""
Cifrado simétrico para secretos 2FA usando Fernet (AES-128-CBC + HMAC-SHA256).
La clave se deriva del SECRET_KEY del sistema.
"""
import base64
import hashlib
from cryptography.fernet import Fernet
from app.core.config import settings


def _get_fernet() -> Fernet:
    """Deriva una clave Fernet de 32 bytes desde el SECRET_KEY del sistema."""
    key_bytes = hashlib.sha256(settings.secret_key.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


def cifrar_secret(secret: str) -> str:
    """Cifra un secreto 2FA antes de guardarlo en la BD."""
    f = _get_fernet()
    return f.encrypt(secret.encode()).decode()


def descifrar_secret(secret_cifrado: str) -> str:
    """Descifra un secreto 2FA leído de la BD."""
    # Compatibilidad: si no está cifrado (instalaciones anteriores), retornarlo tal cual
    if not secret_cifrado.startswith("gAAAAA"):
        return secret_cifrado
    f = _get_fernet()
    return f.decrypt(secret_cifrado.encode()).decode()
