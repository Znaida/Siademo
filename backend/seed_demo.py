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
    ("KronosZnd", "Dirección General",      "Despacho del Director",    None),
    ("KronosZnd", "Dirección General",      "Secretaría General",       "Despacho del Director"),
    ("KronosZnd", "Subdirección Técnica",   "Área de Sistemas",         "Dirección General"),
    ("KronosZnd", "Subdirección Técnica",   "Área de Archivo",          "Dirección General"),
    ("KronosZnd", "Subdirección Jurídica",  "Área Legal",               "Dirección General"),
]

TIPOS = ["RECIBIDA", "ENVIADA", "INTERNA", "NO-RADICABLE"]
ESTADOS = ["Radicado", "En Trámite", "Archivado", "Trasladado"]
SERIES = [
    ("01", "Actas",        "01-01", "Actas de Reunión"),
    ("02", "Contratos",    "02-01", "Contratos de Prestación"),
    ("03", "Informes",     "03-01", "Informes de Gestión"),
    ("04", "Comunicados",  "04-01", "Comunicados Internos"),
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
        print("   Dependencias: 5")
        print("   TRD: 4 series")
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
