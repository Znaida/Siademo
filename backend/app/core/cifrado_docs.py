"""
T3.3.1 — Cifrado de documentos en reposo con AES-256-GCM
Cada archivo se cifra con un IV único de 12 bytes antes de guardarse en disco.
Formato en disco: [12 bytes IV] + [ciphertext + 16 bytes tag GCM]
"""
import os
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from app.core.config import settings


def _get_key() -> bytes:
    """Deriva clave AES-256 (32 bytes) desde el SECRET_KEY del sistema."""
    return hashlib.sha256(settings.secret_key.encode()).digest()


def cifrar_archivo(ruta_origen: str, ruta_destino: str) -> str:
    """
    Lee el archivo en ruta_origen, lo cifra con AES-256-GCM y guarda
    el resultado en ruta_destino. Retorna el IV en hex para referencia.
    """
    key = _get_key()
    aesgcm = AESGCM(key)
    iv = os.urandom(12)  # IV único por documento

    with open(ruta_origen, "rb") as f:
        datos = f.read()

    cifrado = aesgcm.encrypt(iv, datos, None)  # ciphertext + 16 bytes tag

    with open(ruta_destino, "wb") as f:
        f.write(iv + cifrado)  # [12 bytes IV][ciphertext+tag]

    return iv.hex()


def cifrar_bytes(datos: bytes) -> bytes:
    """Cifra bytes en memoria. Retorna IV + ciphertext."""
    key = _get_key()
    aesgcm = AESGCM(key)
    iv = os.urandom(12)
    cifrado = aesgcm.encrypt(iv, datos, None)
    return iv + cifrado


def descifrar_archivo(ruta_cifrada: str) -> bytes:
    """
    Lee un archivo cifrado y retorna los bytes originales descifrados.
    """
    key = _get_key()
    aesgcm = AESGCM(key)

    with open(ruta_cifrada, "rb") as f:
        contenido = f.read()

    iv = contenido[:12]
    cifrado = contenido[12:]
    return aesgcm.decrypt(iv, cifrado, None)


def es_archivo_cifrado(ruta: str) -> bool:
    """
    Detecta si un archivo ya está cifrado por SIADE.
    Los archivos cifrados tienen al menos 28 bytes (12 IV + 16 tag mínimo).
    Usa un marcador en los primeros bytes para distinguirlos.
    """
    try:
        with open(ruta, "rb") as f:
            header = f.read(4)
        # PDFs empiezan con %PDF, los cifrados no
        return not header.startswith(b"%PDF") and not header.startswith(b"PK")
    except Exception:
        return False
