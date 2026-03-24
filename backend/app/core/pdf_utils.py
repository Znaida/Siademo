"""
T4.4.3 — Manejo avanzado de PDFs
- Dividir PDF por páginas o rangos
- Heredar metadatos del documento original (título, autor, fecha, serie, subserie)
- Validar que el archivo sea un PDF real
Tools: pypdf ≥4.0
"""
import os
from io import BytesIO
from pypdf import PdfReader, PdfWriter
from datetime import datetime


def validar_pdf(datos: bytes) -> bool:
    """Verifica que los bytes correspondan a un PDF válido."""
    return datos[:4] == b"%PDF"


def obtener_info_pdf(datos: bytes) -> dict:
    """Extrae información básica del PDF: páginas, metadatos."""
    try:
        reader = PdfReader(BytesIO(datos))
        meta = reader.metadata or {}
        return {
            "num_paginas": len(reader.pages),
            "titulo": meta.get("/Title", ""),
            "autor": meta.get("/Author", ""),
            "creador": meta.get("/Creator", ""),
            "fecha_creacion": meta.get("/CreationDate", ""),
        }
    except Exception as e:
        raise ValueError(f"No se pudo leer el PDF: {str(e)}")


def dividir_pdf_por_paginas(datos: bytes, metadatos_radicado: dict) -> list[dict]:
    """
    Divide un PDF en páginas individuales, heredando metadatos del radicado.
    Retorna lista de dicts con {'pagina': N, 'bytes': bytes, 'nombre': str}
    """
    if not validar_pdf(datos):
        raise ValueError("El archivo no es un PDF válido.")

    reader = PdfReader(BytesIO(datos))
    total = len(reader.pages)
    resultados = []

    for i, page in enumerate(reader.pages):
        writer = PdfWriter()
        writer.add_page(page)

        # Heredar metadatos del radicado original
        writer.add_metadata({
            "/Title": f"{metadatos_radicado.get('asunto', 'Documento')} — Página {i+1} de {total}",
            "/Author": metadatos_radicado.get("nombre_razon_social", "Alcaldía de Manizales"),
            "/Subject": f"Serie: {metadatos_radicado.get('serie', '')} | Subserie: {metadatos_radicado.get('subserie', '')}",
            "/Creator": "SIADE — Sistema Integral de Administración y Gestión Documental",
            "/Producer": "SIADE v1.0",
            "/CreationDate": datetime.now().strftime("D:%Y%m%d%H%M%S"),
            "/Keywords": f"Radicado:{metadatos_radicado.get('nro_radicado', '')} "
                         f"Serie:{metadatos_radicado.get('serie', '')} "
                         f"Subserie:{metadatos_radicado.get('subserie', '')}",
        })

        buf = BytesIO()
        writer.write(buf)
        resultados.append({
            "pagina": i + 1,
            "total_paginas": total,
            "bytes": buf.getvalue(),
            "nombre": f"{metadatos_radicado.get('nro_radicado', 'doc')}_p{i+1:03d}.pdf"
        })

    return resultados


def dividir_pdf_por_rango(datos: bytes, pagina_inicio: int, pagina_fin: int, metadatos_radicado: dict) -> dict:
    """
    Extrae un rango de páginas del PDF heredando metadatos del radicado.
    pagina_inicio y pagina_fin son 1-based.
    """
    if not validar_pdf(datos):
        raise ValueError("El archivo no es un PDF válido.")

    reader = PdfReader(BytesIO(datos))
    total = len(reader.pages)

    if pagina_inicio < 1 or pagina_fin > total or pagina_inicio > pagina_fin:
        raise ValueError(f"Rango inválido. El PDF tiene {total} páginas.")

    writer = PdfWriter()
    for i in range(pagina_inicio - 1, pagina_fin):
        writer.add_page(reader.pages[i])

    writer.add_metadata({
        "/Title": f"{metadatos_radicado.get('asunto', 'Documento')} — Páginas {pagina_inicio}-{pagina_fin}",
        "/Author": metadatos_radicado.get("nombre_razon_social", "Alcaldía de Manizales"),
        "/Subject": f"Serie: {metadatos_radicado.get('serie', '')} | Subserie: {metadatos_radicado.get('subserie', '')}",
        "/Creator": "SIADE — Sistema Integral de Administración y Gestión Documental",
        "/Producer": "SIADE v1.0",
        "/CreationDate": datetime.now().strftime("D:%Y%m%d%H%M%S"),
        "/Keywords": f"Radicado:{metadatos_radicado.get('nro_radicado', '')} "
                     f"Serie:{metadatos_radicado.get('serie', '')}",
    })

    buf = BytesIO()
    writer.write(buf)
    return {
        "pagina_inicio": pagina_inicio,
        "pagina_fin": pagina_fin,
        "total_paginas_extraidas": pagina_fin - pagina_inicio + 1,
        "bytes": buf.getvalue(),
        "nombre": f"{metadatos_radicado.get('nro_radicado', 'doc')}_p{pagina_inicio:03d}-{pagina_fin:03d}.pdf"
    }


def combinar_pdfs(lista_datos: list[bytes], metadatos_radicado: dict) -> dict:
    """Combina múltiples PDFs en uno solo heredando metadatos."""
    writer = PdfWriter()
    total_paginas = 0

    for datos in lista_datos:
        if not validar_pdf(datos):
            continue
        reader = PdfReader(BytesIO(datos))
        for page in reader.pages:
            writer.add_page(page)
            total_paginas += 1

    writer.add_metadata({
        "/Title": metadatos_radicado.get("asunto", "Documento combinado"),
        "/Author": metadatos_radicado.get("nombre_razon_social", "Alcaldía de Manizales"),
        "/Subject": f"Serie: {metadatos_radicado.get('serie', '')} | Subserie: {metadatos_radicado.get('subserie', '')}",
        "/Creator": "SIADE — Sistema Integral de Administración y Gestión Documental",
        "/Producer": "SIADE v1.0",
        "/CreationDate": datetime.now().strftime("D:%Y%m%d%H%M%S"),
    })

    buf = BytesIO()
    writer.write(buf)
    return {
        "total_paginas": total_paginas,
        "bytes": buf.getvalue(),
        "nombre": f"{metadatos_radicado.get('nro_radicado', 'doc')}_combinado.pdf"
    }
