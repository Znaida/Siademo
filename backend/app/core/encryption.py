"""
Cifrado AES-256-GCM para documentos en reposo.
La clave maestra se lee de la variable de entorno DOCUMENT_ENCRYPTION_KEY
(64 caracteres hexadecimales = 32 bytes). Si no está configurada, los
archivos se guardan sin cifrar (modo desarrollo/local).
"""
import os
import secrets
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _get_key() -> bytes | None:
    """Devuelve la clave AES-256 (32 bytes) o None si no está configurada."""
    hex_key = os.getenv("DOCUMENT_ENCRYPTION_KEY", "")
    if not hex_key or len(hex_key) != 64:
        return None
    try:
        return bytes.fromhex(hex_key)
    except ValueError:
        return None


def cifrar_archivo(datos: bytes) -> bytes:
    """
    Cifra datos con AES-256-GCM.
    Formato del resultado: [12 bytes nonce] + [datos cifrados + 16 bytes tag]
    Si no hay clave configurada, devuelve los datos sin modificar.
    """
    key = _get_key()
    if not key:
        return datos

    nonce = secrets.token_bytes(12)  # 96 bits recomendado para GCM
    aesgcm = AESGCM(key)
    cifrado = aesgcm.encrypt(nonce, datos, None)
    return nonce + cifrado


def descifrar_archivo(datos: bytes) -> bytes:
    """
    Descifra datos con AES-256-GCM.
    Si no hay clave o los datos no están cifrados, los devuelve sin modificar.
    """
    key = _get_key()
    if not key or len(datos) < 12:
        return datos

    nonce = datos[:12]
    cifrado = datos[12:]
    aesgcm = AESGCM(key)
    try:
        return aesgcm.decrypt(nonce, cifrado, None)
    except Exception:
        # Si falla el descifrado (ej: archivo antiguo sin cifrar), devolver tal cual
        return datos


def cifrado_activo() -> bool:
    """True si la clave de cifrado está configurada."""
    return _get_key() is not None
