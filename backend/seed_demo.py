"""
T7.1.2 — Seed de datos de demostración para Supabase
Crea usuarios, radicados, trazabilidad y estructura orgánica de ejemplo.
Uso:
    DATABASE_URL='...' python3 seed_demo.py
"""
import os
import sys
import random
from datetime import datetime, timedelta

# Asegurar que puede importar app.*
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import get_db_connection
from app.core.config import pwd_context


# ─── Datos de ejemplo ──────────────────────────────────────────────────────────

USUARIOS = [
    ("ventanilla1",  "Ventanilla2026",  "Ana María Torres",      2),
    ("jefe_archivo", "Archivo2026",     "Carlos Rodríguez",      1),
    ("funcionario1", "Funcio2026",      "Laura Gómez",           2),
    ("funcionario2", "Funcio2026",      "Pedro Martínez",        2),
]

DEPENDENCIAS = [
    # Sección 100 — Despacho del Contralor Municipal
    ("Contraloría de Rionegro", "Despacho del Contralor Municipal",
     "Despacho del Contralor Municipal", None),
    # Subsección 101
    ("Contraloría de Rionegro", "Despacho del Contralor Municipal",
     "Oficina Asesora de Control Interno", "Despacho del Contralor Municipal"),
    # Subsección 102
    ("Contraloría de Rionegro", "Despacho del Contralor Municipal",
     "Oficina Asesora Jurídica", "Despacho del Contralor Municipal"),
    # Sección 110 — Subcontraloría
    ("Contraloría de Rionegro", "Subcontraloría",
     "Subcontraloría", None),
    # Sección 120 — Contraloría Auxiliar de Vigilancia y Control
    ("Contraloría de Rionegro", "Contraloría Auxiliar de Vigilancia y Control",
     "Contraloría Auxiliar de Vigilancia y Control", None),
    # Subsección 121
    ("Contraloría de Rionegro", "Contraloría Auxiliar de Vigilancia y Control",
     "Dirección de Auditorías", "Contraloría Auxiliar de Vigilancia y Control"),
    # Sección 130 — Contraloría Auxiliar de Responsabilidad Fiscal y Jurisdicción Coactiva
    ("Contraloría de Rionegro", "Contraloría Auxiliar de Responsabilidad Fiscal y Jurisdicción Coactiva",
     "Contraloría Auxiliar de Responsabilidad Fiscal y Jurisdicción Coactiva", None),
]

TIPOS = ["RECIBIDA", "ENVIADA", "INTERNA", "NO-RADICABLE"]
ESTADOS = ["Radicado", "En Trámite", "Archivado", "Trasladado"]
SERIES = [
    # 01 — ACCIONES CONSTITUCIONALES
    ("01", "Acciones Constitucionales",     "01-01", "Acciones de Cumplimiento"),
    ("01", "Acciones Constitucionales",     "01-02", "Acciones de Tutela"),
    # 02 — ACTAS
    ("02", "Actas",  "02-01", "Actas de Brigada de Emergencia"),
    ("02", "Actas",  "02-02", "Actas de Comité de Conciliación"),
    ("02", "Actas",  "02-03", "Actas de Comité de Contratación"),
    ("02", "Actas",  "02-04", "Actas de Comité de Control Social"),
    ("02", "Actas",  "02-05", "Actas de Comité de Convivencia Laboral"),
    ("02", "Actas",  "02-06", "Actas de Comité Institucional de Coordinación de Control Interno"),
    ("02", "Actas",  "02-07", "Actas de Comité Institucional de Gestión y Desempeño"),
    ("02", "Actas",  "02-08", "Actas de Comité Paritario de Seguridad y Salud en el Trabajo"),
    ("02", "Actas",  "02-09", "Actas de Comité Técnico de Auditorías"),
    ("02", "Actas",  "02-10", "Actas de Comité Técnico de Sostenibilidad de la Información Financiera"),
    ("02", "Actas",  "02-11", "Actas de Eliminación Documental"),
    ("02", "Actas",  "02-12", "Actas de Reuniones Internas entre Dependencias"),
    # 03 — ACTOS ADMINISTRATIVOS
    ("03", "Actos Administrativos",         "03-01", "Resoluciones"),
    # 04 — AUDITORÍAS TERRITORIALES
    ("04", "Auditorías Territoriales",      "04-01", "Auditorías de Actuación Especial de Fiscalización - AEF"),
    ("04", "Auditorías Territoriales",      "04-02", "Auditorías de Cumplimiento - AC"),
    ("04", "Auditorías Territoriales",      "04-03", "Auditorías de Desempeño - AD"),
    ("04", "Auditorías Territoriales",      "04-04", "Auditorías Financieras de Gestión y Resultados - AFGR"),
    # 05 — CIRCULARES
    ("05", "Circulares",                    "05-01", "Circulares Dispositivas"),
    ("05", "Circulares",                    "05-02", "Circulares Informativas"),
    # 06 — COMPROBANTES CONTABLES
    ("06", "Comprobantes Contables",        "06-01", "Comprobantes Contables de Egresos"),
    ("06", "Comprobantes Contables",        "06-02", "Comprobantes Contables de Ingresos"),
    # 07 — COMPROBANTES DE ALMACÉN
    ("07", "Comprobantes de Almacén",       "07-01", "Comprobantes de Baja de Bienes de Almacén"),
    ("07", "Comprobantes de Almacén",       "07-02", "Comprobantes de Egreso de Bienes de Almacén"),
    ("07", "Comprobantes de Almacén",       "07-03", "Comprobantes de Ingreso de Bienes de Almacén"),
    # 08 — CONCEPTOS
    ("08", "Conceptos",                     "08-01", "Conceptos Jurídicos"),
    # 09 — CONCILIACIONES BANCARIAS (sin subserie)
    ("09", "Conciliaciones Bancarias",      "",      ""),
    # 10 — CONSECUTIVOS DE COMUNICACIONES OFICIALES
    ("10", "Consecutivos de Comunicaciones Oficiales", "10-01", "Enviadas"),
    ("10", "Consecutivos de Comunicaciones Oficiales", "10-02", "Internas"),
    ("10", "Consecutivos de Comunicaciones Oficiales", "10-03", "Recibidas"),
    # 11 — CONTRATOS
    ("11", "Contratos",  "11-01", "Contratos de Arrendamiento"),
    ("11", "Contratos",  "11-02", "Contratos de Comodato"),
    ("11", "Contratos",  "11-03", "Contratos de Compraventa"),
    ("11", "Contratos",  "11-04", "Contratos de Consultoría"),
    ("11", "Contratos",  "11-05", "Contratos de Obras"),
    ("11", "Contratos",  "11-06", "Contratos de Prestación de Servicios"),
    ("11", "Contratos",  "11-07", "Contratos de Seguros"),
    ("11", "Contratos",  "11-08", "Contratos de Suministros"),
    ("11", "Contratos",  "11-09", "Contratos Interadministrativos"),
    ("11", "Contratos",  "11-10", "Contratos Urgencia Manifiesta"),
    # 12 — CONVENIOS
    ("12", "Convenios",  "12-01", "Convenios de Organización o Asociación"),
    ("12", "Convenios",  "12-02", "Convenios de Cooperación Nacional"),
    ("12", "Convenios",  "12-03", "Convenios Interadministrativos"),
    ("12", "Convenios",  "12-04", "Convenios Interinstitucionales"),
    # 13 — DECLARACIONES TRIBUTARIAS (sin subserie)
    ("13", "Declaraciones Tributarias",     "",      ""),
    # 14 — DERECHOS DE PETICIÓN (sin subserie)
    ("14", "Derechos de Petición",          "",      ""),
    # 15 — ESTADOS FINANCIEROS (sin subserie)
    ("15", "Estados Financieros",           "",      ""),
    # 16 — HISTORIALES DE BIENES INMUEBLES (sin subserie)
    ("16", "Historiales de Bienes Inmuebles", "",    ""),
    # 17 — HISTORIALES DE MAQUINARIA Y EQUIPOS (sin subserie)
    ("17", "Historiales de Maquinaria y Equipos", "", ""),
    # 18 — HISTORIALES DE VEHÍCULOS (sin subserie)
    ("18", "Historiales de Vehículos",      "",      ""),
    # 19 — HISTORIAS LABORALES (sin subserie)
    ("19", "Historias Laborales",           "",      ""),
    # 20 — INFORMES
    ("20", "Informes",   "20-01", "Informes a Entes de Control"),
    ("20", "Informes",   "20-02", "Informes de Austeridad de Gasto"),
    ("20", "Informes",   "20-03", "Informes de Conciliación y Defensa Jurídica"),
    ("20", "Informes",   "20-04", "Informes de Ejecución Presupuestal"),
    ("20", "Informes",   "20-05", "Informes de Gestión"),
    ("20", "Informes",   "20-06", "Informes de Revisión de la Cuenta"),
    ("20", "Informes",   "20-07", "Informes de Seguimiento a los Derechos de Petición"),
    ("20", "Informes",   "20-08", "Informes de Seguimiento al Plan Anticorrupción y Atención al Ciudadano"),
    ("20", "Informes",   "20-09", "Informes de Seguimiento de Control Interno"),
    ("20", "Informes",   "20-10", "Informes de Seguimiento de la Segunda Línea de Defensa"),
    ("20", "Informes",   "20-11", "Informe del Estado de Control Interno"),
    ("20", "Informes",   "20-12", "Informes del Sistema de Gestión Seguridad y Salud en el Trabajo"),
    ("20", "Informes",   "20-13", "Informes del Tesoro y del Presupuesto"),
    ("20", "Informes",   "20-14", "Informes sobre el Estado de las Finanzas"),
    ("20", "Informes",   "20-15", "Informes sobre el Estado de los Recursos Naturales y del Medio Ambiente"),
    ("20", "Informes",   "20-16", "Informes Trimestrales de Seguimiento al MIPG"),
    # 21 — INSTRUMENTOS ARCHIVÍSTICOS
    ("21", "Instrumentos Archivísticos",    "21-01", "Bancos Terminológicos de Series y Subseries Documentales"),
    ("21", "Instrumentos Archivísticos",    "21-02", "Cuadros de Clasificación Documental - CCD"),
    ("21", "Instrumentos Archivísticos",    "21-03", "Inventarios Documentales de Archivo Central"),
    ("21", "Instrumentos Archivísticos",    "21-04", "Planes Institucionales de Archivos - PINAR"),
    ("21", "Instrumentos Archivísticos",    "21-05", "Programas de Gestión Documental - PGD"),
    ("21", "Instrumentos Archivísticos",    "21-06", "Tablas de Control de Acceso"),
    ("21", "Instrumentos Archivísticos",    "21-07", "Tablas de Retención Documental - TRD"),
    ("21", "Instrumentos Archivísticos",    "21-08", "Tablas de Valoración Documental - TVD"),
    # 22 — INSTRUMENTOS DE CONTROL
    ("22", "Instrumentos de Control",       "22-01", "De Almacén"),
    ("22", "Instrumentos de Control",       "22-02", "De Ausentismo Laboral"),
    ("22", "Instrumentos de Control",       "22-03", "De Comunicaciones Oficiales"),
    ("22", "Instrumentos de Control",       "22-04", "De Préstamo de Tecnología"),
    ("22", "Instrumentos de Control",       "22-05", "De Préstamos y Consulta de Documentos"),
    ("22", "Instrumentos de Control",       "22-06", "De Publicación de la Información en la Sede Electrónica"),
    # 23 — INSTRUMENTOS DE GESTIÓN DE LA INFORMACIÓN PÚBLICA
    ("23", "Instrumentos de Gestión de la Información Pública", "23-01", "Esquemas de Publicación de Información"),
    ("23", "Instrumentos de Gestión de la Información Pública", "23-02", "Índices de Información Clasificada y Reservada"),
    ("23", "Instrumentos de Gestión de la Información Pública", "23-03", "Registros de Activos de Información"),
    # 24 — LIBROS CONTABLES AUXILIARES (sin subserie)
    ("24", "Libros Contables Auxiliares",   "",      ""),
    # 25 — LIBROS CONTABLES PRINCIPALES
    ("25", "Libros Contables Principales",  "25-01", "Libro Diario"),
    ("25", "Libros Contables Principales",  "25-02", "Libro Mayor"),
    # 26 — MANUALES
    ("26", "Manuales",   "26-01", "Manuales de Atención al Usuario"),
    ("26", "Manuales",   "26-02", "Manuales de Contratación y Supervisión"),
    ("26", "Manuales",   "26-03", "Manuales de Imagen Corporativa"),
    ("26", "Manuales",   "26-04", "Manuales de Políticas Contables y de Operación"),
    ("26", "Manuales",   "26-05", "Manuales de Procesos y Procedimientos"),
    ("26", "Manuales",   "26-06", "Manuales de Publicación de Información Mínima Requerida"),
    ("26", "Manuales",   "26-07", "Manuales del Código de Integridad"),
    ("26", "Manuales",   "26-08", "Manuales del Sistema de Gestión de Calidad"),
    ("26", "Manuales",   "26-09", "Manuales Específicos de Funciones, Requisitos y Competencias Laborales"),
    ("26", "Manuales",   "26-10", "Manuales para el Cumplimiento de la Normativa Aplicable a la Contraloría"),
    # 27 — NÓMINA (sin subserie)
    ("27", "Nómina",                        "",      ""),
    # 28 — PLANES
    ("28", "Planes",     "28-01", "Planes Anticorrupción y Atención al Ciudadano"),
    ("28", "Planes",     "28-02", "Planes Anuales de Adquisiciones"),
    ("28", "Planes",     "28-03", "Planes Anuales de Empleos Vacantes"),
    ("28", "Planes",     "28-04", "Planes de Acción Institucional"),
    ("28", "Planes",     "28-05", "Planes de Auditorías"),
    ("28", "Planes",     "28-06", "Planes de Bienestar Laboral, Estímulos e Incentivos Institucionales"),
    ("28", "Planes",     "28-07", "Planes de Comunicaciones"),
    ("28", "Planes",     "28-08", "Planes de Conservación Documental"),
    ("28", "Planes",     "28-09", "Planes de Mejoramiento Institucional"),
    ("28", "Planes",     "28-10", "Planes de Participación Ciudadana"),
    ("28", "Planes",     "28-11", "Planes de Preservación Digital a Largo Plazo"),
    ("28", "Planes",     "28-12", "Planes de Prevención, Preparación y Respuesta ante Emergencias"),
    ("28", "Planes",     "28-13", "Planes de Previsión de Recursos Humanos"),
    ("28", "Planes",     "28-14", "Planes de Seguridad y Privacidad de la Información"),
    ("28", "Planes",     "28-15", "Planes de Trabajo Anual del SG-SST"),
    ("28", "Planes",     "28-16", "Planes de Transferencias Documentales"),
    ("28", "Planes",     "28-17", "Planes de Tratamientos de Riesgos de Seguridad y Privacidad de la Información"),
    ("28", "Planes",     "28-18", "Planes de Trabajo de Contralores Estudiantiles"),
    ("28", "Planes",     "28-19", "Planes de Vigilancia y Control Fiscal Territorial"),
    ("28", "Planes",     "28-20", "Planes Estratégicos de Talento Humano - PETH"),
    ("28", "Planes",     "28-21", "Planes Estratégicos de TIC - PETI"),
    ("28", "Planes",     "28-22", "Planes Estratégicos Institucionales"),
    ("28", "Planes",     "28-23", "Planes Generales de Auditorías Territoriales"),
    ("28", "Planes",     "28-24", "Planes Institucionales de Capacitación - PIC"),
    # 29 — POLÍTICAS
    ("29", "Políticas",  "29-01", "Políticas de Gestión Ambiental"),
    ("29", "Políticas",  "29-02", "Políticas de Gestión de la Calidad"),
    ("29", "Políticas",  "29-03", "Políticas de Gestión del Riesgo"),
    ("29", "Políticas",  "29-04", "Políticas de Gestión Documental"),
    ("29", "Políticas",  "29-05", "Políticas de Habeas Data"),
    ("29", "Políticas",  "29-06", "Políticas de Integridad"),
    ("29", "Políticas",  "29-07", "Políticas de Tratamientos de Riesgos de Seguridad y Privacidad de la Información"),
    ("29", "Políticas",  "29-08", "Políticas de Seguridad y Salud en el Trabajo"),
    # 30 — PROCESOS ADMINISTRATIVOS SANCIONATORIOS FISCALES (sin subserie)
    ("30", "Procesos Administrativos Sancionatorios Fiscales", "", ""),
    # 31 — PROCESOS CONTRACTUALES DECLARADOS DESIERTOS (sin subserie)
    ("31", "Procesos Contractuales Declarados Desiertos",      "", ""),
    # 32 — PROCESOS JURÍDICOS
    ("32", "Procesos Jurídicos",            "32-01", "Procesos Contenciosos Administrativos"),
    ("32", "Procesos Jurídicos",            "32-02", "Procesos Disciplinarios"),
    # 33 — PROCESOS JURISDICCIÓN COACTIVA (sin subserie)
    ("33", "Procesos Jurisdicción Coactiva", "",     ""),
    # 34 — PROCESOS RESPONSABILIDAD FISCAL
    ("34", "Procesos Responsabilidad Fiscal", "34-01", "Procesos Responsabilidad Fiscal Ordinario"),
    ("34", "Procesos Responsabilidad Fiscal", "34-02", "Procesos Responsabilidad Fiscal Verbal"),
    # 35 — PROGRAMAS
    ("35", "Programas",                     "35-01", "Programas Anuales Mensualizados de Caja - PAC"),
    # 36 — REGISTROS DE OPERACIONES DE CAJA MENOR (sin subserie)
    ("36", "Registros de Operaciones de Caja Menor",           "", ""),
    # 37 — REGLAMENTOS INTERNOS DE RECAUDO DE CARTERA (sin subserie)
    ("37", "Reglamentos Internos de Recaudo de Cartera",       "", ""),
    # 38 — REGLAMENTOS INTERNOS DE TRABAJO (sin subserie)
    ("38", "Reglamentos Internos de Trabajo",                  "", ""),
    # 39 — REPORTES DE ACCIDENTE DE TRABAJO (sin subserie)
    ("39", "Reportes de Accidente de Trabajo",                 "", ""),
    # 40 — REPORTES DE INFORMACIÓN EXÓGENA (sin subserie)
    ("40", "Reportes de Información Exógena",                  "", ""),
    # 41 — SOLICITUDES SGC (sin subserie)
    ("41", "Solicitudes de Elaboración, Modificación o Eliminación de la Documentación del SGC", "", ""),
]
REMITENTES = [
    ("PERSONA_NATURAL", "García",    "Juan",   "CC", "12345678"),
    ("PERSONA_NATURAL", "López",     "María",  "CC", "87654321"),
    ("PERSONA_JURÍDICA", "Tech SAS", "",       "NIT", "900123456-1"),
    ("PERSONA_NATURAL", "Herrera",   "Luis",   "CC", "11223344"),
    ("PERSONA_JURÍDICA", "Consultores ABC", "", "NIT", "800987654-2"),
]
ASUNTOS = [
    "Solicitud de información sobre procesos administrativos",
    "Derecho de petición - Respuesta a comunicación oficial",
    "Informe mensual de actividades del área",
    "Comunicado interno sobre reunión de coordinación",
    "Contrato de prestación de servicios profesionales",
    "Solicitud de certificación de documentos",
    "Radicación de propuesta técnica y económica",
    "Respuesta a requerimiento de ente de control",
    "Comunicación de traslado de expediente",
    "Notificación de acto administrativo",
]


def limpiar_datos_demo(conn, cur):
    """Elimina datos demo anteriores (excepto admin)."""
    print("  Limpiando datos demo anteriores...")
    cur.execute("DELETE FROM trazabilidad_radicados")
    cur.execute("DELETE FROM notificaciones")
    cur.execute("DELETE FROM radicados")
    cur.execute("DELETE FROM archivo_central")
    cur.execute("DELETE FROM estructura_organica")
    cur.execute("DELETE FROM trd")
    cur.execute("DELETE FROM secuencia_radicados")
    cur.execute("DELETE FROM usuarios WHERE rol_id != 0")
    conn.commit()


def crear_usuarios(conn, cur):
    """Crea usuarios de prueba."""
    print("  Creando usuarios...")
    ids = {}
    for usuario, password, nombre, rol in USUARIOS:
        pw_hash = pwd_context.hash(password)
        secret = "JBSWY3DPEHPK3PXP"
        cur.execute("""
            INSERT INTO usuarios (usuario, password_hash, nombre_completo, rol_id, secret_2fa, activo)
            VALUES (?, ?, ?, ?, ?, 1)
        """, (usuario, pw_hash, nombre, rol, secret))
        conn.commit()
        cur.execute("SELECT id FROM usuarios WHERE usuario = ?", (usuario,))
        row = cur.fetchone()
        ids[usuario] = dict(row)["id"]
        print(f"    ✓ {usuario} (rol={rol}, id={ids[usuario]})")
    return ids


def crear_estructura(conn, cur):
    """Crea estructura orgánica de ejemplo."""
    print("  Creando estructura orgánica...")
    for entidad, unidad, oficina, depende_de in DEPENDENCIAS:
        cur.execute("""
            INSERT INTO estructura_organica (entidad, unidad, oficina, depende_de)
            VALUES (?, ?, ?, ?)
        """, (entidad, unidad, oficina, depende_de))
    conn.commit()
    print(f"    ✓ {len(DEPENDENCIAS)} dependencias creadas")


def crear_trd(conn, cur):
    """Crea TRD básica."""
    print("  Creando TRD...")
    for cod_serie, serie, cod_sub, subserie in SERIES:
        cur.execute("""
            INSERT INTO trd (cod_unidad, unidad, cod_oficina, oficina,
                             cod_serie, nombre_serie, cod_subserie, nombre_subserie,
                             tipo_documental, soporte, extension,
                             años_gestion, años_central, disposicion_final,
                             porcentaje_seleccion, procedimiento, llaves_busqueda)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("01", "Secretaría General", "01-01", "Despacho",
              cod_serie, serie, cod_sub, subserie,
              "Físico/Digital", "Papel/Electrónico", ".pdf",
              2, 8, "Eliminación", 10, "Digitalizar antes de eliminar",
              f"{serie},{subserie}"))
    conn.commit()
    print(f"    ✓ {len(SERIES)} series TRD creadas")


def crear_radicados(conn, cur, user_ids):
    """Crea 30 radicados de ejemplo con variedad de tipos, estados y fechas."""
    print("  Creando radicados...")
    usuario_ids = list(user_ids.values())
    admin_id = None
    cur.execute("SELECT id FROM usuarios WHERE rol_id = 0 LIMIT 1")
    row = cur.fetchone()
    if row:
        admin_id = dict(row)["id"]

    contadores = {"RAD": 0, "ENV": 0, "INT": 0, "NR": 0}
    prefijos = {"RECIBIDA": "RAD", "ENVIADA": "ENV", "INTERNA": "INT", "NO-RADICABLE": "NR"}
    anio = 2026

    radicados_creados = []

    for i in range(30):
        tipo = TIPOS[i % len(TIPOS)]
        prefijo = prefijos[tipo]
        contadores[prefijo] += 1
        nro = f"{prefijo}-{anio}-{contadores[prefijo]:05d}"

        # Fechas distribuidas en los últimos 6 meses
        dias_atras = random.randint(1, 180)
        fecha = (datetime.now() - timedelta(days=dias_atras)).strftime("%Y-%m-%d %H:%M:%S")
        fecha_venc = (datetime.now() + timedelta(days=random.randint(5, 30))).strftime("%Y-%m-%d")

        remitente = REMITENTES[i % len(REMITENTES)]
        serie_data = SERIES[i % len(SERIES)]
        asunto = ASUNTOS[i % len(ASUNTOS)]
        estado = ESTADOS[i % len(ESTADOS)]
        funcionario_id = usuario_ids[i % len(usuario_ids)] if usuario_ids else admin_id
        dependencias_lista = [d[2] for d in DEPENDENCIAS]
        seccion = dependencias_lista[i % len(dependencias_lista)]

        cur.execute("""
            INSERT INTO radicados (
                nro_radicado, tipo_radicado, tipo_remitente,
                primer_apellido, nombre_razon_social,
                tipo_documento, nro_documento,
                asunto, serie, subserie, tipo_documental,
                fecha_radicacion, fecha_vencimiento,
                dias_respuesta, nro_folios,
                seccion_responsable, funcionario_responsable_id,
                estado, paso_actual, pasos_completados,
                creado_por, metodo_recepcion,
                hash_sha256
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            nro, tipo, remitente[0],
            remitente[1], remitente[2],
            remitente[3], remitente[4],
            asunto, serie_data[1], serie_data[3], "Digital",
            fecha, fecha_venc,
            random.randint(5, 15), random.randint(1, 10),
            seccion, funcionario_id,
            estado, "ventanillaRadica", "[]",
            admin_id, "Ventanilla",
            f"hash_demo_{nro}_{i:03d}"
        ))
        conn.commit()

        cur.execute("SELECT id FROM radicados WHERE nro_radicado = ?", (nro,))
        row = cur.fetchone()
        rad_id = dict(row)["id"] if row else None
        radicados_creados.append((nro, estado, admin_id, funcionario_id, fecha))

        # Actualizar secuencia
        cur.execute("""
            INSERT INTO secuencia_radicados (prefijo, anio, ultimo_numero)
            VALUES (?, ?, ?)
            ON CONFLICT (prefijo, anio) DO UPDATE SET ultimo_numero = EXCLUDED.ultimo_numero
        """, (prefijo, anio, contadores[prefijo]))
        conn.commit()

    print(f"    ✓ 30 radicados creados")
    return radicados_creados


def crear_trazabilidad(conn, cur, radicados):
    """Crea trazabilidad para los radicados."""
    print("  Creando trazabilidad...")
    for nro, estado, creado_por, funcionario_id, fecha in radicados:
        cur.execute("""
            INSERT INTO trazabilidad_radicados
                (nro_radicado, accion, comentario, desde_usuario_id, hacia_usuario_id, estado_nuevo, fecha)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (nro, "CREACION", "Radicado creado en ventanilla.",
              creado_por, funcionario_id, "Radicado", fecha))

        if estado in ("En Trámite", "Archivado", "Trasladado"):
            cur.execute("""
                INSERT INTO trazabilidad_radicados
                    (nro_radicado, accion, comentario, desde_usuario_id, hacia_usuario_id, estado_nuevo, fecha)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (nro, "TRASLADO", "Asignado para trámite.",
                  creado_por, funcionario_id, "En Trámite", fecha))

        if estado == "Archivado":
            cur.execute("""
                INSERT INTO trazabilidad_radicados
                    (nro_radicado, accion, comentario, desde_usuario_id, hacia_usuario_id, estado_nuevo, fecha)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (nro, "ARCHIVADO", "Radicado archivado exitosamente.",
                  funcionario_id, None, "Archivado", fecha))

    conn.commit()
    print(f"    ✓ Trazabilidad creada para {len(radicados)} radicados")


def main():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("ERROR: Define DATABASE_URL antes de correr este script")
        sys.exit(1)

    print(f"\n🌱 Iniciando seed de datos demo en Supabase...")
    print(f"   URL: {db_url[:40]}...")

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        limpiar_datos_demo(conn, cur)
        user_ids = crear_usuarios(conn, cur)
        crear_estructura(conn, cur)
        crear_trd(conn, cur)
        radicados = crear_radicados(conn, cur, user_ids)
        crear_trazabilidad(conn, cur, radicados)

        print("\n✅ Seed completado exitosamente!")
        print("   Usuarios creados:", len(USUARIOS))
        print("   Radicados creados: 30")
        print(f"   Dependencias: {len(DEPENDENCIAS)}")
        print(f"   TRD: {len(SERIES)} series/subseries")
        print("\n   Credenciales de prueba:")
        print("   - admin / Admin2026 (administrador)")
        for u, p, n, r in USUARIOS:
            print(f"   - {u} / {p} ({n})")
        print("   2FA para todos: JBSWY3DPEHPK3PXP")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error en seed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
