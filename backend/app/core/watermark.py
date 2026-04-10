"""
Marca de Agua Dinámica — SIADE
==============================
Proyecta una marca de agua transparente sobre cada página de un PDF con:
  - Código de barras Code128 del número de radicado (encabezado)
  - Nombre del usuario que descarga, timestamp e IP
  - Texto diagonal semitransparente al centro

El PDF marcado se genera en memoria; nunca se escribe a disco.
Si el archivo NO es PDF, retorna los bytes sin modificar.
"""

import io
from datetime import datetime


def _generar_barcode_bytes(nro_radicado: str) -> bytes | None:
    """Genera imagen PNG del código de barras Code128 del nro_radicado."""
    try:
        import barcode
        from barcode.writer import ImageWriter

        writer = ImageWriter()
        code = barcode.get("code128", nro_radicado, writer=writer)
        buf = io.BytesIO()
        code.write(buf, options={
            "module_height": 6,
            "text_distance": 1,
            "font_size": 4,
            "quiet_zone": 2,
            "write_text": True,
        })
        buf.seek(0)
        return buf.read()
    except Exception as e:
        print(f"[WATERMARK] No se pudo generar barcode: {e}")
        return None


def aplicar_marca_agua(
    contenido: bytes,
    nombre_usuario: str,
    ip: str,
    filename: str = "",
    nro_radicado: str = ""
) -> bytes:
    """
    Recibe el contenido binario de un archivo y retorna una copia con marca de agua.
    Solo actúa sobre PDFs. Para cualquier otro tipo de archivo devuelve los bytes tal cual.

    Args:
        contenido: bytes del archivo (ya descifrado si aplica)
        nombre_usuario: nombre completo o usuario del descargador
        ip: dirección IP del cliente
        filename: nombre del archivo, para detectar extensión
        nro_radicado: número del radicado para incluir en el código de barras

    Returns:
        bytes del PDF marcado, o bytes originales si no es PDF
    """
    es_pdf = filename.lower().endswith(".pdf") or contenido[:4] == b"%PDF"
    if not es_pdf:
        return contenido

    try:
        import fitz  # PyMuPDF

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        texto_cabecera = f"COPIA NO CONTROLADA  |  {nombre_usuario}  |  {timestamp}  |  IP: {ip}"

        # Generar imagen del barcode si hay nro_radicado
        barcode_bytes = _generar_barcode_bytes(nro_radicado) if nro_radicado else None

        doc = fitz.open(stream=contenido, filetype="pdf")
        font = fitz.Font("helv")

        for pagina in doc:
            ancho = pagina.rect.width
            alto  = pagina.rect.height

            # ── Encabezado con código de barras ──────────────────────────────
            alto_header = 36 if barcode_bytes else 26

            pagina.draw_rect(
                fitz.Rect(0, 0, ancho, alto_header),
                color=(1, 0.93, 0.76),
                fill=(1, 0.93, 0.76),
                fill_opacity=0.80,
            )

            if barcode_bytes:
                # Insertar barcode en el lado derecho del header
                try:
                    ancho_bc = min(120, ancho * 0.35)
                    rect_bc = fitz.Rect(ancho - ancho_bc - 4, 2, ancho - 4, alto_header - 2)
                    pagina.insert_image(rect_bc, stream=barcode_bytes)
                except Exception:
                    pass  # Si el barcode falla, continúa sin él

            # Texto del header (izquierda)
            pagina.insert_text(
                fitz.Point(6, 12),
                texto_cabecera,
                fontsize=6.5,
                color=(0.55, 0.27, 0),
                fontname="helv",
                rotate=0,
            )
            if nro_radicado:
                pagina.insert_text(
                    fitz.Point(6, 24),
                    f"Radicado: {nro_radicado}",
                    fontsize=7.5,
                    color=(0.55, 0.27, 0),
                    fontname="helv",
                    rotate=0,
                )

            # ── Texto diagonal semitransparente ──────────────────────────────
            texto_diagonal = f"{nombre_usuario}  |  {timestamp}  |  IP: {ip}"
            punto_ancla   = fitz.Point(ancho * 0.08, alto * 0.60)
            matriz_rot    = fitz.Matrix(45)

            writer = fitz.TextWriter(pagina.rect, opacity=0.18, color=(0.4, 0.4, 0.4))
            writer.append(punto_ancla, texto_diagonal, font=font, fontsize=24)
            writer.write_text(pagina, morph=(punto_ancla, matriz_rot))

            # ── Franja inferior ───────────────────────────────────────────────
            pagina.draw_rect(
                fitz.Rect(0, alto - 22, ancho, alto),
                color=(1, 0.93, 0.76),
                fill=(1, 0.93, 0.76),
                fill_opacity=0.75,
            )
            pagina.insert_text(
                fitz.Point(6, alto - 7),
                f"Descargado de SIADE — {texto_cabecera}",
                fontsize=5.5,
                color=(0.55, 0.27, 0),
                fontname="helv",
                rotate=0,
            )

        buf = io.BytesIO()
        doc.save(buf, garbage=4, deflate=True)
        doc.close()
        return buf.getvalue()

    except Exception as e:
        print(f"[WATERMARK] No se pudo aplicar marca de agua: {e}")
        return contenido
