import os
import sqlite3


def get_db_connection():
    if os.getenv("WEBSITE_HOSTNAME"):
        db_path = "/home/site/wwwroot/storage/database.db"
    else:
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        db_path = os.path.join(BASE_DIR, "..", "storage", "database.db")

    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def inicializar_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            nombre_completo TEXT NOT NULL,
            rol_id INTEGER NOT NULL,
            secret_2fa TEXT,
            activo INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS radicados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nro_radicado TEXT UNIQUE NOT NULL,
            tipo_radicado TEXT NOT NULL,
            tipo_remitente TEXT,
            primer_apellido TEXT,
            segundo_apellido TEXT,
            nombre_razon_social TEXT,
            tipo_documento TEXT,
            nro_documento TEXT,
            cargo TEXT,
            direccion TEXT,
            telefono TEXT,
            correo_electronico TEXT,
            pais TEXT,
            departamento TEXT,
            ciudad TEXT,
            serie TEXT,
            subserie TEXT,
            tipo_documental TEXT,
            asunto TEXT,
            metodo_recepcion TEXT,
            nro_guia TEXT,
            nro_folios INTEGER,
            dias_respuesta INTEGER,
            fecha_vencimiento TEXT,
            anexo_nombre TEXT,
            descripcion_anexo TEXT,
            seccion_responsable TEXT,
            funcionario_responsable_id INTEGER,
            con_copia TEXT,
            seccion_origen TEXT,
            funcionario_origen_id INTEGER,
            nro_radicado_relacionado TEXT,
            activa_flujo_id INTEGER,
            path_principal TEXT,
            anexos_json TEXT,
            creado_por INTEGER,
            estado TEXT DEFAULT 'Radicado'
        );
        CREATE TABLE IF NOT EXISTS auditoria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            accion TEXT,
            modulo TEXT,
            detalle TEXT,
            ip_origen TEXT,
            fecha_accion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS equipos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL
        );
        CREATE TABLE IF NOT EXISTS usuario_equipo (
            usuario_id INTEGER,
            equipo_id INTEGER,
            PRIMARY KEY (usuario_id, equipo_id)
        );
        CREATE TABLE IF NOT EXISTS estructura_organica (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entidad TEXT,
            unidad TEXT,
            oficina TEXT,
            depende_de TEXT
        );
        CREATE TABLE IF NOT EXISTS trd (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cod_unidad TEXT, unidad TEXT, cod_oficina TEXT, oficina TEXT,
            cod_serie TEXT, nombre_serie TEXT, cod_subserie TEXT, nombre_subserie TEXT,
            tipo_documental TEXT, soporte TEXT, extension TEXT,
            años_gestion INTEGER, años_central INTEGER,
            disposicion_final TEXT, porcentaje_seleccion INTEGER, procedimiento TEXT,
            llaves_busqueda TEXT
        );
        CREATE TABLE IF NOT EXISTS secuencia_radicados (
            prefijo TEXT,
            anio INTEGER,
            ultimo_numero INTEGER DEFAULT 0,
            PRIMARY KEY (prefijo, anio)
        );
        CREATE TABLE IF NOT EXISTS trazabilidad_radicados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nro_radicado TEXT NOT NULL,
            accion TEXT NOT NULL,
            comentario TEXT,
            desde_usuario_id INTEGER,
            hacia_usuario_id INTEGER,
            estado_nuevo TEXT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS notificaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            nro_radicado TEXT NOT NULL,
            mensaje TEXT NOT NULL,
            leida INTEGER DEFAULT 0,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS archivo_central (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nro_radicado TEXT NOT NULL UNIQUE,
            serie TEXT,
            subserie TEXT,
            tipo_documental TEXT,
            asunto TEXT,
            anio_produccion INTEGER,
            caja TEXT,
            carpeta TEXT,
            folio_inicio INTEGER,
            folio_fin INTEGER,
            llaves_busqueda TEXT,
            observaciones TEXT,
            disposicion_final TEXT,
            path_principal TEXT,
            fecha_transferencia TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            transferido_por INTEGER
        );
    """)
    conn.commit()

    # Migración: agregar columnas faltantes
    columnas_nuevas = [
        ("tipo_remitente", "TEXT"), ("primer_apellido", "TEXT"), ("segundo_apellido", "TEXT"),
        ("tipo_documento", "TEXT"), ("nro_documento", "TEXT"), ("cargo", "TEXT"),
        ("direccion", "TEXT"), ("telefono", "TEXT"), ("correo_electronico", "TEXT"),
        ("pais", "TEXT"), ("departamento", "TEXT"), ("ciudad", "TEXT"),
        ("serie", "TEXT"), ("subserie", "TEXT"), ("tipo_documental", "TEXT"),
        ("metodo_recepcion", "TEXT"), ("nro_guia", "TEXT"), ("nro_folios", "INTEGER"),
        ("dias_respuesta", "INTEGER"), ("anexo_nombre", "TEXT"), ("descripcion_anexo", "TEXT"),
        ("seccion_responsable", "TEXT"), ("funcionario_responsable_id", "INTEGER"),
        ("con_copia", "TEXT"), ("seccion_origen", "TEXT"), ("funcionario_origen_id", "INTEGER"),
        ("nro_radicado_relacionado", "TEXT"), ("activa_flujo_id", "INTEGER"),
        ("estado", "TEXT DEFAULT 'Radicado'"),
    ]
    for col, tipo in columnas_nuevas:
        try:
            cur.execute(f"ALTER TABLE radicados ADD COLUMN {col} {tipo}")
            conn.commit()
        except Exception:
            pass

    # Backfill trazabilidad
    cur.execute("""
        INSERT INTO trazabilidad_radicados (nro_radicado, accion, comentario, desde_usuario_id, hacia_usuario_id, estado_nuevo, fecha)
        SELECT r.nro_radicado, 'CREACION', 'Radicado creado en ventanilla.', r.creado_por, r.funcionario_responsable_id, 'Radicado',
               COALESCE((SELECT fecha_accion FROM auditoria WHERE modulo='VENTANILLA' AND detalle LIKE '%' || r.nro_radicado || '%' ORDER BY fecha_accion ASC LIMIT 1), CURRENT_TIMESTAMP)
        FROM radicados r
        WHERE r.nro_radicado NOT IN (SELECT nro_radicado FROM trazabilidad_radicados WHERE accion = 'CREACION')
    """)
    conn.commit()
    conn.close()
