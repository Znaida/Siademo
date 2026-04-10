"""
update_trd.py — Actualiza SOLO dependencias y TRD en Azure/Supabase
SIN tocar radicados, usuarios ni ningún otro dato existente.

Uso:
    DATABASE_URL='postgresql://...' python3 update_trd.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import get_db_connection

# ─── Estructura orgánica — Contraloría Municipal de Rionegro ──────────────────

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

# ─── Series y subseries CCD — Contraloría Municipal de Rionegro ───────────────

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
    # 09 — CONCILIACIONES BANCARIAS
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
    # 13 — DECLARACIONES TRIBUTARIAS
    ("13", "Declaraciones Tributarias",     "",      ""),
    # 14 — DERECHOS DE PETICIÓN
    ("14", "Derechos de Petición",          "",      ""),
    # 15 — ESTADOS FINANCIEROS
    ("15", "Estados Financieros",           "",      ""),
    # 16 — HISTORIALES DE BIENES INMUEBLES
    ("16", "Historiales de Bienes Inmuebles", "",    ""),
    # 17 — HISTORIALES DE MAQUINARIA Y EQUIPOS
    ("17", "Historiales de Maquinaria y Equipos", "", ""),
    # 18 — HISTORIALES DE VEHÍCULOS
    ("18", "Historiales de Vehículos",      "",      ""),
    # 19 — HISTORIAS LABORALES
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
    ("22", "Instrumentos de Control",       "22-02", "De Archivo"),
    ("22", "Instrumentos de Control",       "22-03", "De Bienes"),
    ("22", "Instrumentos de Control",       "22-04", "De Correspondencia"),
    ("22", "Instrumentos de Control",       "22-05", "De Personal"),
    # 23 — NOTIFICACIONES JUDICIALES Y EXTRAJUDICIALES
    ("23", "Notificaciones Judiciales y Extrajudiciales", "", ""),
    # 24 — PLANES
    ("24", "Planes",     "24-01", "Planes de Acción"),
    ("24", "Planes",     "24-02", "Planes de Mejoramiento Institucional"),
    ("24", "Planes",     "24-03", "Planes de Mejoramiento por Procesos"),
    ("24", "Planes",     "24-04", "Planes de Mejoramiento Sujetos Vigilados"),
    ("24", "Planes",     "24-05", "Planes de Prevención del Daño Antijurídico"),
    # 25 — PRESUPUESTO
    ("25", "Presupuesto", "25-01", "Presupuesto de Gastos"),
    ("25", "Presupuesto", "25-02", "Presupuesto de Ingresos"),
    # 26 — PROCESOS ADMINISTRATIVOS SANCIONATORIOS
    ("26", "Procesos Administrativos Sancionatorios", "", ""),
    # 27 — PROCESOS DISCIPLINARIOS
    ("27", "Procesos Disciplinarios",       "", ""),
    # 28 — PROCESOS FISCALES
    ("28", "Procesos Fiscales",             "28-01", "Procesos de Responsabilidad Fiscal"),
    ("28", "Procesos Fiscales",             "28-02", "Procesos de Jurisdicción Coactiva"),
    # 29 — PROYECTOS
    ("29", "Proyectos",  "29-01", "Proyectos de Cooperación"),
    ("29", "Proyectos",  "29-02", "Proyectos de Inversión"),
    # 30 — REGLAMENTOS
    ("30", "Reglamentos", "30-01", "Reglamentos Internos de Trabajo"),
    # 31 — SEGUROS
    ("31", "Seguros",    "31-01", "Pólizas de Seguros"),
    # 32 — SOLICITUDES
    ("32", "Solicitudes", "32-01", "Solicitudes de Certificaciones"),
    ("32", "Solicitudes", "32-02", "Solicitudes de Información"),
]


def main():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("ERROR: Define DATABASE_URL antes de correr este script")
        print("Uso: DATABASE_URL='postgresql://...' python3 update_trd.py")
        sys.exit(1)

    print("\n🔄 Actualizando TRD y estructura orgánica en Azure...")
    print(f"   URL: {db_url[:40]}...")

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # ── 1. Actualizar estructura orgánica ──────────────────────────────────
        print("\n  Limpiando estructura orgánica anterior...")
        cur.execute("DELETE FROM estructura_organica")
        conn.commit()

        print("  Insertando dependencias de Contraloría de Rionegro...")
        for entidad, unidad, oficina, depende_de in DEPENDENCIAS:
            cur.execute("""
                INSERT INTO estructura_organica (entidad, unidad, oficina, depende_de)
                VALUES (?, ?, ?, ?)
            """, (entidad, unidad, oficina, depende_de))
        conn.commit()
        print(f"    ✓ {len(DEPENDENCIAS)} dependencias insertadas")

        # ── 2. Actualizar TRD ──────────────────────────────────────────────────
        print("\n  Limpiando TRD anterior...")
        cur.execute("DELETE FROM trd")
        conn.commit()

        print("  Insertando series/subseries CCD Contraloría de Rionegro...")
        for cod_serie, serie, cod_sub, subserie in SERIES:
            cur.execute("""
                INSERT INTO trd (
                    cod_unidad, unidad, cod_oficina, oficina,
                    cod_serie, nombre_serie, cod_subserie, nombre_subserie,
                    tipo_documental, soporte, extension,
                    años_gestion, años_central, disposicion_final,
                    porcentaje_seleccion, procedimiento, llaves_busqueda
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "01", "Contraloría de Rionegro",
                "01-01", "Despacho del Contralor Municipal",
                cod_serie, serie, cod_sub, subserie,
                "Físico/Digital", "Papel/Electrónico", ".pdf",
                2, 8, "Eliminación",
                10, "Digitalizar antes de eliminar",
                f"{serie},{subserie}"
            ))
        conn.commit()
        print(f"    ✓ {len(SERIES)} series/subseries insertadas")

        print("\n✅ Actualización completada exitosamente!")
        print(f"   Dependencias: {len(DEPENDENCIAS)}")
        print(f"   Series TRD:   {len(SERIES)}")
        print("\n   ⚠️  Radicados y usuarios NO fueron modificados.")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error durante la actualización: {e}")
        sys.exit(1)
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
