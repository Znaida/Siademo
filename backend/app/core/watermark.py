"""
Marca de Agua Dinámica — SIADE
==============================
Proyecta una marca de agua transparente sobre cada página de un PDF con:
  - Nombre del usuario que descarga
  - Timestamp de la descarga
  - IP de origen

El PDF marcado se genera en memoria; nunca se escribe a disco.
Si el archivo NO es PDF, retorna los bytes sin modificar.
"""

import io
from datetime import datetime


def aplicar_marca_agua(contenido: bytes, nombre_usuario: str, ip: str, filename: str = "") -> bytes:
    """
    Recibe el contenido binario de un archivo y retorna una copia con marca de agua.
    Solo actúa sobre PDFs. Para cualquier otro tipo de archivo devuelve los bytes tal cual.

    Args:
        contenido: bytes del archivo (ya descifrado si aplica)
        nombre_usuario: nombre completo o usuario del descargador
        ip: dirección IP del cliente
        filename: nombre del archivo, para detectar extensión

    Returns:
        bytes del PDF marcado, o bytes originales si no es PDF
    """
    # Solo procesamos PDFs
    es_pdf = filename.lower().endswith(".pdf") or contenido[:4] == b"%PDF"
    if not es_pdf:
        return contenido

    try:
        import fitz  # PyMuPDF

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        texto_cabecera = f"COPIA NO CONTROLADA  |  {nombre_usuario}  |  {timestamp}  |  IP: {ip}"

        doc = fitz.open(stream=contenido, filetype="pdf")
        font = fitz.Font("helv")

        for pagina in doc:
            ancho = pagina.rect.width
            alto  = pagina.rect.height

            # ── Franja superior (color ámbar suave) ─────────────────────────
            pagina.draw_rect(
                fitz.Rect(0, 0, ancho, 26),
                color=(1, 0.93, 0.76),
                fill=(1, 0.93, 0.76),
                fill_opacity=0.75,
            )
            pagina.insert_text(
                fitz.Point(8, 17),
                texto_cabecera,
                fontsize=7,
                color=(0.55, 0.27, 0),
                fontname="helv",
                rotate=0,
            )

            # ── Texto diagonal con TextWriter + Matrix(45°) ─────────────────
            texto_diagonal = f"{nombre_usuario}  |  {timestamp}  |  IP: {ip}"
            punto_ancla   = fitz.Point(ancho * 0.08, alto * 0.60)
            matriz_rot    = fitz.Matrix(45)   # rotación 45 grados

            writer = fitz.TextWriter(pagina.rect, opacity=0.18, color=(0.4, 0.4, 0.4))
            writer.append(punto_ancla, texto_diagonal, font=font, fontsize=24)
            writer.write_text(pagina, morph=(punto_ancla, matriz_rot))

            # ── Franja inferior ──────────────────────────────────────────────
            pagina.draw_rect(
                fitz.Rect(0, alto - 24, ancho, alto),
                color=(1, 0.93, 0.76),
                fill=(1, 0.93, 0.76),
                fill_opacity=0.75,
            )
            pagina.insert_text(
                fitz.Point(8, alto - 8),
                f"Descargado de SIADE — {texto_cabecera}",
                fontsize=6,
                color=(0.55, 0.27, 0),
                fontname="helv",
                rotate=0,
            )

        buf = io.BytesIO()
        doc.save(buf, garbage=4, deflate=True)
        doc.close()
        return buf.getvalue()

    except Exception as e:
        # Si algo falla (PDF corrupto, etc.) retornamos el original sin marca
        print(f"[WATERMARK] No se pudo aplicar marca de agua: {e}")
        return contenido
