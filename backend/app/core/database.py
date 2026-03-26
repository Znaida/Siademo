import os
import sqlite3

# ── PostgreSQL support (opcional) ─────────────────────────────────────────────
try:
    import psycopg2
    import psycopg2.extras
    _PSYCOPG2 = True
except ImportError:
    _PSYCOPG2 = False


def is_postgres() -> bool:
    """True cuando DATABASE_URL está definida y NO estamos en modo test."""
    return bool(os.getenv("DATABASE_URL")) and not bool(os.getenv("TEST_DB_PATH"))


def _get_psycopg2():
    """Importa psycopg2 en tiempo de ejecución para evitar problemas de startup."""
    try:
        import psycopg2 as pg
        import psycopg2.extras
        return pg
    except ImportError:
        return None


# ── Wrappers PostgreSQL ────────────────────────────────────────────────────────

class _PgCursor:
    """Envuelve psycopg2 RealDictCursor para comportarse como sqlite3.Cursor."""

    def __init__(self, cursor):
        self._cur = cursor

    def execute(self, sql: str, params=None):
        sql = sql.replace("?", "%s")
        self._cur.execute(sql, params) if params else self._cur.execute(sql)
        return self

    def executemany(self, sql: str, params):
        sql = sql.replace("?", "%s")
        self._cur.executemany(sql, params)
        return self

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    @property
    def lastrowid(self):
        """Emula sqlite3 lastrowid usando PostgreSQL lastval()."""
        self._cur.execute("SELECT lastval()")
        row = self._cur.fetchone()
        return row["lastval"] if row else None

    @property
    def rowcount(self):
        return self._cur.rowcount

    def close(self):
        self._cur.close()

    def __iter__(self):
        return iter(self._cur)


class _PgConnection:
    """Envuelve psycopg2 connection para comportarse como sqlite3.Connection."""

    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        return _PgCursor(cur)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def execute(self, sql: str, params=None):
        cur = self.cursor()
        cur.execute(sql, params)
        return cur


# ── Fábrica de conexiones ──────────────────────────────────────────────────────

def get_db_connection():
    """Retorna conexión SQLite o PostgreSQL según variables de entorno."""

    # Modo test: siempre SQLite aislado
    if os.getenv("TEST_DB_PATH"):
        db_path = os.getenv("TEST_DB_PATH")
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # Producción con Supabase/PostgreSQL
    if is_postgres():
        pg = _get_psycopg2()
        if pg:
            conn = pg.connect(os.getenv("DATABASE_URL"))
            return _PgConnection(conn)

    # Desarrollo local: SQLite
    if os.getenv("WEBSITE_HOSTNAME"):
        db_path = "/home/site/wwwroot/storage/database.db"
    else:
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        db_path = os.path.join(BASE_DIR, "..", "storage", "database.db")

    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


# ── Inicialización del esquema ─────────────────────────────────────────────────

def inicializar_db():
    """Crea las tablas si no existen. Compatible con SQLite y PostgreSQL."""
    pg = is_postgres() and (_get_psycopg2() is not None)
    pk = "SERIAL PRIMARY KEY" if pg else "INTEGER PRIMARY KEY AUTOINCREMENT"

    conn = get_db_connection()
    cur = conn.cursor()

    tablas = [
        f"""CREATE TABLE IF NOT EXISTS usuarios (
            id {pk},
            usuario TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            nombre_completo TEXT NOT NULL,
            rol_id INTEGER NOT NULL,
            secret_2fa TEXT,
            activo INTEGER DEFAULT 1,
            debe_cambiar_password INTEGER DEFAULT 0
        )""",
        f"""CREATE TABLE IF NOT EXISTS radicados (
            id {pk},
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
            fecha_radicacion TEXT,
            hash_sha256 TEXT,
            paso_actual TEXT DEFAULT 'ventanillaRadica',
            pasos_completados TEXT DEFAULT '[]',
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
        )""",
        f"""CREATE TABLE IF NOT EXISTS auditoria (
            id {pk},
            usuario_id INTEGER,
            accion TEXT,
            modulo TEXT,
            detalle TEXT,
            ip_origen TEXT,
            fecha_accion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        f"""CREATE TABLE IF NOT EXISTS equipos (
            id {pk},
            nombre TEXT UNIQUE NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS usuario_equipo (
            usuario_id INTEGER,
            equipo_id INTEGER,
            PRIMARY KEY (usuario_id, equipo_id)
        )""",
        f"""CREATE TABLE IF NOT EXISTS estructura_organica (
            id {pk},
            entidad TEXT,
            unidad TEXT,
            oficina TEXT,
            depende_de TEXT
        )""",
        f"""CREATE TABLE IF NOT EXISTS trd (
            id {pk},
            cod_unidad TEXT, unidad TEXT, cod_oficina TEXT, oficina TEXT,
            cod_serie TEXT, nombre_serie TEXT, cod_subserie TEXT, nombre_subserie TEXT,
            tipo_documental TEXT, soporte TEXT, extension TEXT,
            años_gestion INTEGER, años_central INTEGER,
            disposicion_final TEXT, porcentaje_seleccion INTEGER, procedimiento TEXT,
            llaves_busqueda TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS secuencia_radicados (
            prefijo TEXT,
            anio INTEGER,
            ultimo_numero INTEGER DEFAULT 0,
            PRIMARY KEY (prefijo, anio)
        )""",
        f"""CREATE TABLE IF NOT EXISTS trazabilidad_radicados (
            id {pk},
            nro_radicado TEXT NOT NULL,
            accion TEXT NOT NULL,
            comentario TEXT,
            desde_usuario_id INTEGER,
            hacia_usuario_id INTEGER,
            estado_nuevo TEXT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        f"""CREATE TABLE IF NOT EXISTS notificaciones (
            id {pk},
            usuario_id INTEGER NOT NULL,
            nro_radicado TEXT NOT NULL,
            mensaje TEXT NOT NULL,
            leida INTEGER DEFAULT 0,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        f"""CREATE TABLE IF NOT EXISTS archivo_central (
            id {pk},
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
        )""",
    ]

    for sql in tablas:
        cur.execute(sql)
    conn.commit()

    # Migraciones: solo necesarias para SQLite (DBs existentes)
    if not pg:
        _migrar_columnas_sqlite(conn, cur)

    # Backfill trazabilidad
    cur.execute("""
        INSERT INTO trazabilidad_radicados
            (nro_radicado, accion, comentario, desde_usuario_id, hacia_usuario_id, estado_nuevo, fecha)
        SELECT r.nro_radicado, 'CREACION', 'Radicado creado en ventanilla.',
               r.creado_por, r.funcionario_responsable_id, 'Radicado', CURRENT_TIMESTAMP
        FROM radicados r
        WHERE r.nro_radicado NOT IN (
            SELECT nro_radicado FROM trazabilidad_radicados WHERE accion = 'CREACION'
        )
    """)
    conn.commit()
    conn.close()


def _migrar_columnas_sqlite(conn, cur):
    """Agrega columnas faltantes en SQLite (soporte migraciones incrementales)."""
    for col, tipo in [("debe_cambiar_password", "INTEGER DEFAULT 0")]:
        try:
            cur.execute(f"ALTER TABLE usuarios ADD COLUMN {col} {tipo}")
            conn.commit()
        except Exception:
            pass

    columnas_rad = [
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
        ("estado", "TEXT DEFAULT 'Radicado'"), ("fecha_radicacion", "TEXT"),
        ("hash_sha256", "TEXT"), ("paso_actual", "TEXT DEFAULT 'ventanillaRadica'"),
        ("pasos_completados", "TEXT DEFAULT '[]'"),
    ]
    for col, tipo in columnas_rad:
        try:
            cur.execute(f"ALTER TABLE radicados ADD COLUMN {col} {tipo}")
            conn.commit()
        except Exception:
            pass
