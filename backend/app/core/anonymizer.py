"""
Anonimización de datos sensibles para roles de análisis/desarrollo.
Enmascara PII (nombre, documento, correo, teléfono, dirección) dejando
visible solo la información mínima necesaria para el proceso documental.
"""
import re


def _mask_name(name: str | None) -> str | None:
    """'Juan García López' → 'J*** G*** L***'"""
    if not name:
        return name
    parts = name.strip().split()
    return " ".join(p[0] + "***" if len(p) > 1 else p for p in parts)


def _mask_document(doc: str | None) -> str | None:
    """'12345678' → '****5678' (muestra últimos 4 dígitos)"""
    if not doc:
        return doc
    if len(doc) <= 4:
        return "****"
    return "*" * (len(doc) - 4) + doc[-4:]


def _mask_email(email: str | None) -> str | None:
    """'juan.garcia@empresa.com' → 'j***@***.com'"""
    if not email or "@" not in email:
        return email
    local, domain = email.split("@", 1)
    masked_local = local[0] + "***" if local else "***"
    parts = domain.split(".")
    masked_domain = "***." + parts[-1] if parts else "***"
    return f"{masked_local}@{masked_domain}"


def _mask_phone(phone: str | None) -> str | None:
    """'3001234567' → '300***4567'"""
    if not phone:
        return phone
    digits = re.sub(r"\D", "", phone)
    if len(digits) < 4:
        return "****"
    return digits[:3] + "*" * (len(digits) - 6) + digits[-3:] if len(digits) >= 6 else "****"


def _mask_address(address: str | None) -> str | None:
    """'Calle 45 # 23-10 Apto 301' → 'C*** *** # ***'"""
    if not address:
        return address
    parts = address.split()
    masked = [p[0] + "***" if len(p) > 2 else "***" for p in parts[:3]]
    return " ".join(masked) + (" ..." if len(parts) > 3 else "")


def anonimizar_radicado(radicado: dict) -> dict:
    """
    Recibe un dict de radicado y devuelve una copia con PII enmascarada.
    Los campos no sensibles (serie, estado, fechas, tipo) permanecen visibles.
    """
    r = dict(radicado)
    r["nombre_razon_social"] = _mask_name(r.get("nombre_razon_social"))
    r["primer_apellido"] = _mask_name(r.get("primer_apellido"))
    r["segundo_apellido"] = _mask_name(r.get("segundo_apellido"))
    r["nro_documento"] = _mask_document(r.get("nro_documento"))
    r["correo_electronico"] = _mask_email(r.get("correo_electronico"))
    r["telefono"] = _mask_phone(r.get("telefono"))
    r["direccion"] = _mask_address(r.get("direccion"))
    r["cargo"] = "***" if r.get("cargo") else r.get("cargo")
    r["_anonimizado"] = True
    return r
