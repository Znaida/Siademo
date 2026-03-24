"""
T4.5.1 — Parser de facturas electrónicas DIAN (UBL 2.1)
Parsea XML de facturas DIAN Colombia sin consumir APIs externas.
Extrae: CUFE, NIT proveedor, fecha, número factura, valor total, descripción.
Tools: lxml (stdlib xml.etree como fallback)
"""

import re
from datetime import datetime
from typing import Optional

# Namespaces estándar UBL 2.1 DIAN Colombia
NS = {
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "inv": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
    "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
    "ds":  "http://www.w3.org/2000/09/xmldsig#",
    "xades": "http://uri.etsi.org/01903/v1.3.2#",
    "sts": "dian:gov:co:facturaelectronica:Structures-2-1",
}


def _texto(elem, path: str, ns: dict) -> str:
    """Extrae el texto de un elemento XML por xpath relativo."""
    if elem is None:
        return ""
    found = elem.find(path, ns)
    return (found.text or "").strip() if found is not None else ""


def parsear_factura_dian(xml_bytes: bytes) -> dict:
    """
    Parsea el XML de una factura electrónica DIAN UBL 2.1.
    Retorna dict con los campos relevantes para radicación.
    Lanza ValueError si el XML no tiene la estructura esperada.
    """
    try:
        from lxml import etree as ET
        root = ET.fromstring(xml_bytes)

        def texto(path):
            found = root.find(path, NS)
            if found is None:
                return ""
            return (found.text or "").strip()

        def texto_en(base_elem, path):
            if base_elem is None:
                return ""
            found = base_elem.find(path, NS)
            if found is None:
                return ""
            return (found.text or "").strip()

    except ImportError:
        # Fallback: xml.etree (stdlib), sin validación avanzada
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml_bytes.decode("utf-8", errors="replace"))

        def texto(path):
            # Ajustar namespaces para ElementTree
            found = root.find(path, NS)
            if found is None:
                return ""
            return (found.text or "").strip()

        def texto_en(base_elem, path):
            if base_elem is None:
                return ""
            found = base_elem.find(path, NS)
            if found is None:
                return ""
            return (found.text or "").strip()

    # --- Validar que sea un documento DIAN UBL ---
    tag = root.tag
    es_factura = "Invoice" in tag
    es_nota_debito = "DebitNote" in tag
    es_nota_credito = "CreditNote" in tag

    if not (es_factura or es_nota_debito or es_nota_credito):
        raise ValueError(
            "El XML no corresponde a una Factura, Nota Débito o Nota Crédito DIAN UBL 2.1"
        )

    tipo_documento = (
        "Factura Electrónica" if es_factura
        else "Nota Débito" if es_nota_debito
        else "Nota Crédito"
    )

    # --- Datos básicos del documento ---
    nro_factura     = texto("cbc:ID")
    cufe            = texto("cbc:UUID")
    fecha_emision   = texto("cbc:IssueDate")          # YYYY-MM-DD
    hora_emision    = texto("cbc:IssueTime")
    moneda          = texto("cbc:DocumentCurrencyCode")
    nota_factura    = texto("cbc:Note")

    # --- Proveedor (quien factura) ---
    supplier = root.find("cac:AccountingSupplierParty", NS)
    if supplier is None:
        supplier = root.find("cac:SellerSupplierParty", NS)
    party_sup = supplier.find("cac:Party", NS) if supplier is not None else None

    nit_proveedor   = texto_en(party_sup, "cac:PartyTaxScheme/cbc:CompanyID")
    if not nit_proveedor:
        nit_proveedor = texto_en(party_sup, "cac:PartyIdentification/cbc:ID")
    nombre_proveedor = texto_en(party_sup, "cac:PartyTaxScheme/cbc:RegistrationName")
    if not nombre_proveedor:
        nombre_proveedor = texto_en(party_sup, "cac:PartyName/cbc:Name")
    direccion_proveedor = texto_en(
        party_sup,
        "cac:PhysicalLocation/cac:Address/cac:AddressLine/cbc:Line"
    )
    ciudad_proveedor = texto_en(
        party_sup,
        "cac:PhysicalLocation/cac:Address/cbc:CityName"
    )
    correo_proveedor = texto_en(party_sup, "cac:Contact/cbc:ElectronicMail")
    telefono_proveedor = texto_en(party_sup, "cac:Contact/cbc:Telephone")

    # --- Receptor (Alcaldía de Manizales) ---
    customer = root.find("cac:AccountingCustomerParty", NS)
    party_cust = customer.find("cac:Party", NS) if customer is not None else None
    nit_receptor    = texto_en(party_cust, "cac:PartyTaxScheme/cbc:CompanyID")
    nombre_receptor = texto_en(party_cust, "cac:PartyTaxScheme/cbc:RegistrationName")
    if not nombre_receptor:
        nombre_receptor = texto_en(party_cust, "cac:PartyName/cbc:Name")

    # --- Totales monetarios ---
    totales = root.find("cac:LegalMonetaryTotal", NS)
    valor_bruto       = texto_en(totales, "cbc:LineExtensionAmount")
    descuentos        = texto_en(totales, "cbc:AllowanceTotalAmount")
    subtotal          = texto_en(totales, "cbc:TaxExclusiveAmount")
    impuestos_total   = texto_en(totales, "cbc:TaxInclusiveAmount")
    valor_pagar       = texto_en(totales, "cbc:PayableAmount")

    # --- IVA / impuestos ---
    tax_total = root.find("cac:TaxTotal", NS)
    iva_monto  = texto_en(tax_total, "cbc:TaxAmount")

    # --- Ítems de la factura (resumen) ---
    items = []
    for line in root.findall("cac:InvoiceLine", NS) or root.findall("cac:CreditNoteLine", NS) or root.findall("cac:DebitNoteLine", NS):
        desc = texto_en(line, "cac:Item/cbc:Description")
        qty  = texto_en(line, "cbc:InvoicedQuantity") or texto_en(line, "cbc:CreditedQuantity") or texto_en(line, "cbc:DebitedQuantity")
        unit = texto_en(line, "cbc:InvoicedQuantity")  # atributo unitCode no extraído como texto
        val  = texto_en(line, "cbc:LineExtensionAmount")
        items.append({
            "descripcion": desc,
            "cantidad": qty,
            "valor_linea": val
        })

    # --- Forma de pago ---
    pago = root.find("cac:PaymentMeans", NS)
    forma_pago = texto_en(pago, "cbc:PaymentMeansCode")
    fecha_vence_pago = texto_en(pago, "cbc:PaymentDueDate")

    # --- Construir asunto para radicación ---
    valor_display = f"${float(valor_pagar):,.0f}" if valor_pagar else "N/D"
    asunto_radicacion = (
        f"{tipo_documento} {nro_factura} de {nombre_proveedor} "
        f"por {valor_display} COP — CUFE: {cufe[:16]}..." if cufe else
        f"{tipo_documento} {nro_factura} de {nombre_proveedor} por {valor_display} COP"
    )

    return {
        # Identificación
        "tipo_documento":      tipo_documento,
        "nro_factura":         nro_factura,
        "cufe":                cufe,
        "fecha_emision":       fecha_emision,
        "hora_emision":        hora_emision,
        "moneda":              moneda or "COP",
        "nota":                nota_factura,

        # Proveedor
        "nit_proveedor":       nit_proveedor,
        "nombre_proveedor":    nombre_proveedor,
        "direccion_proveedor": direccion_proveedor,
        "ciudad_proveedor":    ciudad_proveedor,
        "correo_proveedor":    correo_proveedor,
        "telefono_proveedor":  telefono_proveedor,

        # Receptor
        "nit_receptor":        nit_receptor,
        "nombre_receptor":     nombre_receptor,

        # Totales
        "valor_bruto":         valor_bruto,
        "descuentos":          descuentos,
        "subtotal":            subtotal,
        "iva":                 iva_monto,
        "valor_total_con_iva": impuestos_total,
        "valor_a_pagar":       valor_pagar,

        # Pago
        "forma_pago":          forma_pago,
        "fecha_vence_pago":    fecha_vence_pago,

        # Ítems
        "items":               items,

        # Para radicación automática
        "asunto_radicacion":   asunto_radicacion,
        "serie_sugerida":      "Gestión Financiera",
        "subserie_sugerida":   "Facturas de Proveedores",
    }


def validar_xml_dian(xml_bytes: bytes) -> dict:
    """
    Validación estructural básica (sin firma digital DIAN).
    Retorna {'valido': bool, 'errores': list[str], 'advertencias': list[str]}
    """
    errores = []
    advertencias = []

    # 1. Verificar que sea XML válido
    try:
        try:
            from lxml import etree as ET
            root = ET.fromstring(xml_bytes)
        except ImportError:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(xml_bytes.decode("utf-8", errors="replace"))
    except Exception as e:
        return {"valido": False, "errores": [f"XML malformado: {str(e)}"], "advertencias": []}

    tag = root.tag
    if not any(t in tag for t in ["Invoice", "DebitNote", "CreditNote"]):
        errores.append("El documento no es una Factura, Nota Débito o Nota Crédito UBL 2.1")

    # 2. Verificar campos obligatorios DIAN
    campos_req = [
        ("cbc:ID", "Número de factura"),
        ("cbc:UUID", "CUFE"),
        ("cbc:IssueDate", "Fecha de emisión"),
        ("cac:AccountingSupplierParty", "Datos del proveedor"),
        ("cac:AccountingCustomerParty", "Datos del receptor"),
        ("cac:LegalMonetaryTotal", "Totales monetarios"),
    ]
    for xpath, nombre in campos_req:
        if root.find(xpath, NS) is None:
            errores.append(f"Falta campo obligatorio: {nombre} ({xpath})")

    # 3. Verificar CUFE (64 chars hex)
    cufe_el = root.find("cbc:UUID", NS)
    if cufe_el is not None and cufe_el.text:
        cufe = cufe_el.text.strip()
        if len(cufe) < 32:
            advertencias.append(f"CUFE demasiado corto ({len(cufe)} chars). Podría ser inválido.")

    # 4. Verificar fecha
    fecha_el = root.find("cbc:IssueDate", NS)
    if fecha_el is not None and fecha_el.text:
        try:
            datetime.strptime(fecha_el.text.strip(), "%Y-%m-%d")
        except ValueError:
            errores.append("Formato de fecha inválido. Se esperaba YYYY-MM-DD")

    # 5. Verificar valor a pagar
    totales = root.find("cac:LegalMonetaryTotal", NS)
    if totales is not None:
        pagar_el = totales.find("cbc:PayableAmount", NS)
        if pagar_el is None:
            advertencias.append("No se encontró cbc:PayableAmount en totales")

    return {
        "valido": len(errores) == 0,
        "errores": errores,
        "advertencias": advertencias
    }
