import os
import shutil # Para mover archivos a la carpeta de almacenamiento
import random
#import psycopg2
#import psycopg2.extras 
import pyotp
import qrcode
import hashlib
import json
import pandas as pd
import sqlite3  

from io import BytesIO
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from passlib.context import CryptContext
from jose import jwt, JWTError
import os

load_dotenv()

def get_db_connection():
    # Detectamos la ruta según el entorno
    if os.getenv("WEBSITE_HOSTNAME"):
        # Ruta persistente en Azure (/home persiste entre reinicios)
        db_path = "/home/site/wwwroot/storage/database.db"
    else:
        # Ruta en PC local
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(BASE_DIR, "..", "storage", "database.db")

    # CRÍTICO: Crear el directorio si no existe (necesario en Azure primer arranque)
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def inicializar_db_alfa():
    conn = get_db_connection()
    cur = conn.cursor()
    # Script simplificado para SQLite
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
            creado_por INTEGER
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
        CREATE TABLE IF NOT EXISTS workflow_instances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nro_radicado TEXT NOT NULL UNIQUE,
            tipo_flujo TEXT NOT NULL,
            paso_actual TEXT NOT NULL,
            pasos_completados TEXT DEFAULT '[]',
            estado TEXT DEFAULT 'activo',
            iniciado_por INTEGER,
            fecha_inicio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS facturas_dian (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nro_radicado TEXT,
            tipo_documento TEXT,
            nro_factura TEXT UNIQUE NOT NULL,
            cufe TEXT,
            fecha_emision TEXT,
            nit_proveedor TEXT,
            nombre_proveedor TEXT,
            correo_proveedor TEXT,
            telefono_proveedor TEXT,
            direccion_proveedor TEXT,
            ciudad_proveedor TEXT,
            nit_receptor TEXT,
            nombre_receptor TEXT,
            valor_bruto TEXT,
            descuentos TEXT,
            iva TEXT,
            valor_a_pagar TEXT,
            moneda TEXT DEFAULT 'COP',
            forma_pago TEXT,
            fecha_vence_pago TEXT,
            items_json TEXT,
            path_xml TEXT,
            radicado_automatico INTEGER DEFAULT 0,
            estado TEXT DEFAULT 'pendiente',
            creado_por INTEGER,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()

    # Migración: agregar columnas faltantes a tabla radicados si ya existía con esquema viejo
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
            pass  # La columna ya existe

    # Backfill: crear entrada CREACION en trazabilidad para radicados que no la tienen aún
    cur.execute("""
        INSERT INTO trazabilidad_radicados (nro_radicado, accion, comentario, desde_usuario_id, hacia_usuario_id, estado_nuevo, fecha)
        SELECT r.nro_radicado, 'CREACION', 'Radicado creado en ventanilla.', r.creado_por, r.funcionario_responsable_id, 'Radicado',
               COALESCE((SELECT fecha_accion FROM auditoria WHERE modulo='VENTANILLA' AND detalle LIKE '%' || r.nro_radicado || '%' ORDER BY fecha_accion ASC LIMIT 1), CURRENT_TIMESTAMP)
        FROM radicados r
        WHERE r.nro_radicado NOT IN (SELECT nro_radicado FROM trazabilidad_radicados WHERE accion = 'CREACION')
    """)
    conn.commit()

    conn.close()

# Llamamos a la función para que la DB esté lista al encender
inicializar_db_alfa()
app = FastAPI(title="SIADE - Motor de Gestión Documental")

# --- 1. CONFIGURACIÓN DE DIRECTORIOS Y CORS ---
# UPLOAD_DIR = "uploads/radicados" este funciona en el local

if os.getenv("WEBSITE_HOSTNAME"):
    # Ruta persistente en Azure App Service para Linux
    UPLOAD_DIR = "/home/site/wwwroot/storage"
else:
    # Ruta para tu Windows local (un nivel arriba de /backend)
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    UPLOAD_DIR = os.path.join(BASE_DIR, "..", "storage")

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- 2. CONFIGURACIÓN DE CORS ---
#origins = [
#    "http://localhost:4200",
#    "http://127.0.0.1:4200",
#    "http://localhost",
#    "http://127.0.0.1",
    # Azure
#    "https://ashy-desert-090fd4a0f.2.azurestaticapps.net",
#    "https://kronosdemos-fbeyekffbfe9fre7.brazilsouth-01.azurewebsites.net",
#]

origins = [
    "https://ashy-desert-090fd4a0f.2.azurestaticapps.net",
    "http://localhost:4200", # Por si pruebas localmente con Angular
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 3. CONFIGURACIÓN DE SEGURIDAD ---
SECRET_KEY = os.getenv("SECRET_KEY", "dev_local_key_cambiar_en_produccion_2026")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def firmar_resultado(resultado: int):
    texto_a_cifrar = f"{resultado}{SECRET_KEY}"
    return hashlib.sha256(texto_a_cifrar.encode()).hexdigest()

def verificar_password(password_plano, password_hash):
    return pwd_context.verify(password_plano, password_hash)

# --- 4. ESQUEMAS DE DATOS (PYDANTIC) ---

class DependenciaCreate(BaseModel):
    entidad: str
    unidad_administrativa: str
    oficina_productora: str
    relacion_jerarquica: Optional[str] = "Nivel Raíz"

class TRDCreate(BaseModel):
    cod_unidad: str
    unidad: str
    cod_oficina: str
    oficina: str
    cod_serie: str
    nombre_serie: str
    cod_subserie: Optional[str] = None
    nombre_subserie: Optional[str] = None
    tipo_documental: str
    soporte: str
    extension: str
    años_gestion: int
    años_central: int
    disposicion_final: str
    porcentaje_seleccion: int
    procedimiento: str

class RadicadoMetadata(BaseModel):
    tipo_radicado: str  # RECIBIDA, ENVIADA, INTERNA
    tipo_remitente: str
    primer_apellido: Optional[str] = None
    segundo_apellido: Optional[str] = None
    nombre_razon_social: str
    tipo_documento: str
    nro_documento: str
    cargo: Optional[str] = None
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    correo_electronico: Optional[str] = None
    pais: str = "Colombia"
    departamento: str
    ciudad: str
    serie: str
    subserie: str
    tipo_documental: str
    asunto: str
    metodo_recepcion: str
    seccion_origen: Optional[str] = None
    funcionario_origen_id: Optional[int] = None
    nro_guia: Optional[str] = None
    nro_folios: int = 1
    dias_respuesta: int = 15
    anexo_nombre: Optional[str] = None
    descripcion_anexo: Optional[str] = None
    seccion_responsable: str
    funcionario_responsable_id: int
    con_copia: Optional[str] = None
    nro_radicado_relacionado: Optional[str] = None 
    activa_flujo_id: Optional[int] = None          

class UserStatusUpdate(BaseModel):
    user_id: int
    nuevo_estado: bool

#Esquema para creación de equipos de trabajo
class EquipoCreate(BaseModel):
    nombre: str

#Esquema para asignar un usuario a múltiples equipos (Checkboxes)
class AsignacionEquipos(BaseModel):
    usuario_id: int
    equipos_ids: List[int]

#PARA CREAR USUARIOS
class UserCreate(BaseModel):
    usuario: str
    password: str
    nombre_completo: str
    rol_id: int

# --- 5. DEPENDENCIAS Y CONEXIÓN ---

def _decodificar_token(request: Request) -> dict:
    """Decodifica y valida el JWT de la petición. Distingue expirado vs inválido."""
    from jose import ExpiredSignatureError
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token no proporcionado")
    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Token inválido: use el access_token, no el refresh_token")
        return payload
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Sesión expirada. Inicie sesión nuevamente")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")


async def obtener_usuario_actual(request: Request):
    payload = _decodificar_token(request)
    return {"usuario": payload.get("sub"), "rol": payload.get("rol"), "id": payload.get("id_usuario")}


async def obtener_admin_actual(request: Request):
    payload = _decodificar_token(request)
    rol = payload.get("rol")
    if rol is None or rol > 1:
        raise HTTPException(status_code=403, detail="Acceso denegado: se requiere rol Administrador o superior")
    return {"usuario": payload.get("sub"), "rol": rol, "id": payload.get("id_usuario")}


async def obtener_superadmin_actual(request: Request):
    """Solo SuperAdmin (rol 0) puede acceder."""
    payload = _decodificar_token(request)
    if payload.get("rol") != 0:
        raise HTTPException(status_code=403, detail="Acceso denegado: se requiere rol Super Administrador")
    return {"usuario": payload.get("sub"), "rol": 0, "id": payload.get("id_usuario")}


async def verificar_rol_minimo(request: Request, rol_minimo: int) -> dict:
    """Verifica que el usuario tenga un rol <= rol_minimo (menor = más privilegios)."""
    payload = _decodificar_token(request)
    rol = payload.get("rol")
    if rol is None or rol > rol_minimo:
        raise HTTPException(status_code=403, detail=f"Acceso denegado: rol insuficiente")
    return {"usuario": payload.get("sub"), "rol": rol, "id": payload.get("id_usuario")}

# --- 6. FUNCIONES DE APOYO (AUDITORÍA Y SECUENCIA) ---

def registrar_evento(usuario_id, accion, modulo, detalle, request: Request):
    try:
        conn = get_db_connection(); cur = conn.cursor()
        ip_cliente = request.client.host
        cur.execute(
            """INSERT INTO auditoria (usuario_id, accion, modulo, detalle, ip_origen) 
               VALUES (?, ?, ?, ?, ?)""",
            (usuario_id, accion, modulo, detalle, ip_cliente)
        )
        conn.commit(); cur.close(); conn.close()
    except Exception as e:
        print(f"Error crítico en auditoría: {e}")

def generar_consecutivo(prefijo: str):
    anio_actual = datetime.now().year
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Intentamos actualizar primero
        cur.execute("""
            UPDATE secuencia_radicados 
            SET ultimo_numero = ultimo_numero + 1 
            WHERE prefijo = ? AND anio = ?
        """, (prefijo, anio_actual))
        
        # Si no actualizó nada (es el primero del año), insertamos
        if cur.rowcount == 0:
            cur.execute("""
                INSERT INTO secuencia_radicados (prefijo, anio, ultimo_numero)
                VALUES (?, ?, 1)
            """, (prefijo, anio_actual))
            nuevo_valor = 1
        else:
            cur.execute("SELECT ultimo_numero FROM secuencia_radicados WHERE prefijo = ? AND anio = ?", (prefijo, anio_actual))
            nuevo_valor = cur.fetchone()[0]
            
        conn.commit()
        return f"{prefijo}-{anio_actual}-{nuevo_valor:05d}"
    except Exception as e:
        conn.rollback()
        print(f"Error en consecutivo: {e}")
        return None
    finally:
        cur.close(); conn.close()

# --- 7. SETUP INICIAL (solo funciona si no hay ningún admin) ---

@app.post("/admin/setup")
async def setup_inicial():
    """Crea el primer administrador usando variables de entorno de Azure.
    Solo funciona una vez — si ya existe un admin (rol_id=0), retorna error 403."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) as total FROM usuarios WHERE rol_id = 0")
        if cur.fetchone()['total'] > 0:
            raise HTTPException(status_code=403, detail="El sistema ya tiene un administrador. Endpoint deshabilitado.")

        admin_user = os.getenv("ADMIN_USER")
        admin_pass = os.getenv("ADMIN_PASS")
        admin_name = os.getenv("ADMIN_NAME", "Administrador de Sistema")

        if not admin_user or not admin_pass:
            raise HTTPException(status_code=500, detail="Variables ADMIN_USER y ADMIN_PASS no están configuradas en el servidor.")

        from app.core.crypto import cifrar_secret
        password_hash = pwd_context.hash(admin_pass)
        secret_2fa = pyotp.random_base32()
        secret_cifrado = cifrar_secret(secret_2fa)

        cur.execute("""
            INSERT INTO usuarios (usuario, password_hash, nombre_completo, rol_id, secret_2fa, activo)
            VALUES (?, ?, ?, 0, ?, 1)
        """, (admin_user, password_hash, admin_name, secret_cifrado))
        conn.commit()

        # Generar QR code en base64
        from io import BytesIO
        import base64
        uri = pyotp.totp.TOTP(secret_2fa).provisioning_uri(name=admin_user, issuer_name="SIADE")
        qr_img = qrcode.make(uri)
        buf = BytesIO()
        qr_img.save(buf, format="PNG")
        qr_b64 = base64.b64encode(buf.getvalue()).decode()

        return {
            "mensaje": "✅ Administrador creado exitosamente",
            "usuario": admin_user,
            "nombre": admin_name,
            "secret_2fa": secret_2fa,
            "qr_code": f"data:image/png;base64,{qr_b64}",
            "tip": "Escanea el QR con Google Authenticator o ingresa el secret_2fa manualmente"
        }
    finally:
        cur.close()
        conn.close()

# --- 8. ENDPOINTS DE AUTENTICACIÓN ---

@app.get("/auth/captcha")
def generar_captcha():
    num1 = random.randint(1, 10); num2 = random.randint(1, 10)
    resultado = num1 + num2
    return {"pregunta": f"{num1} + {num2}", "captcha_token": firmar_resultado(resultado)}

@app.post("/auth/login")
async def login(request: Request, usuario: str = Form(...), password: str = Form(...), 
                captcha_res: int = Form(...), captcha_token: str = Form(...)):
    if firmar_resultado(captcha_res) != captcha_token:
        raise HTTPException(status_code=401, detail="Captcha incorrecto")

    conn = get_db_connection(); cur = conn.cursor()
    cur.execute("SELECT id, password_hash, rol_id FROM usuarios WHERE usuario = ? AND activo = TRUE", (usuario,))
    user = cur.fetchone()
    
    if not user or not verificar_password(password, user['password_hash']):
        registrar_evento(None, 'LOGIN_FAILED', 'AUTH', f'Fallo: {usuario}', request)
        raise HTTPException(status_code=401, detail="Usuario inactivo o credenciales inválidas")

    registrar_evento(user['id'], 'LOGIN_PASO_1', 'AUTH', 'Acceso paso 1', request)
    cur.close(); conn.close()
    return {"status": "success", "usuario": usuario}

@app.post("/auth/verify-2fa")
async def verify_2fa(request: Request, usuario: str = Form(...), codigo: str = Form(...)):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute("SELECT id, secret_2fa, rol_id FROM usuarios WHERE usuario = ?", (usuario,))
    user = cur.fetchone()
    from app.core.crypto import descifrar_secret
    secret_raw = user['secret_2fa'] if user['secret_2fa'] else "JBSWY3DPEHPK3PXP"
    secret = descifrar_secret(secret_raw)
    totp = pyotp.TOTP(secret)
    if totp.verify(codigo, valid_window=1):
        # Access token: 30 minutos
        access_data = {"sub": usuario, "id_usuario": user['id'], "rol": user['rol_id'],
                       "type": "access", "exp": datetime.utcnow() + timedelta(minutes=30)}
        access_token = jwt.encode(access_data, SECRET_KEY, algorithm=ALGORITHM)
        # Refresh token: 7 días
        refresh_data = {"sub": usuario, "id_usuario": user['id'], "rol": user['rol_id'],
                        "type": "refresh", "exp": datetime.utcnow() + timedelta(days=7)}
        refresh_token = jwt.encode(refresh_data, SECRET_KEY, algorithm=ALGORITHM)

        conn2 = get_db_connection(); cur2 = conn2.cursor()
        cur2.execute("SELECT debe_cambiar_password FROM usuarios WHERE id = ?", (user['id'],))
        u = cur2.fetchone()
        conn2.close()

        registrar_evento(user['id'], 'LOGIN_SUCCESS', 'AUTH', 'Sesión iniciada', request)
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "rol": user['rol_id'],
            "debe_cambiar_password": bool(u['debe_cambiar_password']) if u else False
        }
    else:
        raise HTTPException(status_code=401, detail="TOTP inválido")

@app.post("/auth/2fa/setup")
async def setup_2fa(user_info: dict = Depends(obtener_usuario_actual)):
    """Genera nuevo secreto TOTP + QR para el usuario autenticado."""
    from app.core.crypto import cifrar_secret
    from io import BytesIO
    import base64 as b64mod
    conn = get_db_connection(); cur = conn.cursor()
    try:
        secret_2fa = pyotp.random_base32()
        secret_cifrado = cifrar_secret(secret_2fa)
        usuario = user_info['usuario']
        uri = pyotp.totp.TOTP(secret_2fa).provisioning_uri(name=usuario, issuer_name="SIADE")
        qr_img = qrcode.make(uri)
        buf = BytesIO()
        qr_img.save(buf, format="PNG")
        qr_b64 = b64mod.b64encode(buf.getvalue()).decode()
        cur.execute("UPDATE usuarios SET secret_2fa = ? WHERE usuario = ?", (secret_cifrado, usuario))
        conn.commit()
        return {
            "secret_2fa": secret_2fa,
            "qr_code": f"data:image/png;base64,{qr_b64}",
            "instrucciones": "Escanea el QR con Google Authenticator. El código anterior quedará inválido."
        }
    finally:
        conn.close()


@app.post("/auth/refresh")
async def refresh_token(refresh_token: str = Form(...)):
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Token no es de tipo refresh")
        usuario = payload.get("sub")
        usuario_id = payload.get("id_usuario")
        rol = payload.get("rol")
        # Generar nuevo access token
        access_data = {"sub": usuario, "id_usuario": usuario_id, "rol": rol,
                       "type": "access", "exp": datetime.utcnow() + timedelta(minutes=30)}
        nuevo_token = jwt.encode(access_data, SECRET_KEY, algorithm=ALGORITHM)
        return {"access_token": nuevo_token, "token_type": "bearer"}
    except Exception:
        raise HTTPException(status_code=401, detail="Refresh token inválido o expirado")


# --- 8. RADICACIÓN OFICIAL DE COMUNICACIONES ---

@app.post("/radicar")
async def radicar_oficial(
    request: Request,
    metadata: str = Form(...), # Recibimos el JSON del formulario como string
    archivo_principal: UploadFile = File(...),
    anexos: List[UploadFile] = File(None),
    user_info: dict = Depends(obtener_usuario_actual)
):
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # 1. Parsear metadata de Angular
        data = RadicadoMetadata.parse_raw(metadata)
        
        # 2. Generar el número oficial (RAD-2026-REC-XXXXX)
        prefix_map = {'RECIBIDA': 'RAD', 'ENVIADA': 'ENV', 'INTERNA': 'INV', 'NO-RADICABLE': 'NOR'}
        prefijo = prefix_map.get(data.tipo_radicado, 'NOR')
        nro_radicado = generar_consecutivo(prefijo)
        
        # 3. Almacenamiento físico de archivo principal (cifrado AES-256-GCM)
        from app.core.cifrado_docs import cifrar_bytes
        ext = archivo_principal.filename.split(".")[-1]
        path_p = f"{UPLOAD_DIR}/{nro_radicado}_principal.{ext}.enc"
        contenido_principal = await archivo_principal.read()
        with open(path_p, "wb") as f:
            f.write(cifrar_bytes(contenido_principal))

        # 4. Procesar Anexos (cifrados)
        rutas_anexos = []
        if anexos:
            for i, anexo in enumerate(anexos):
                a_ext = anexo.filename.split(".")[-1]
                path_a = f"{UPLOAD_DIR}/{nro_radicado}_anexo_{i}.{a_ext}.enc"
                contenido_anexo = await anexo.read()
                with open(path_a, "wb") as f:
                    f.write(cifrar_bytes(contenido_anexo))
                rutas_anexos.append(path_a)

        # 5. Calcular Fecha Vencimiento en días hábiles colombianos
        from app.core.dias_habiles import agregar_dias_habiles
        vencimiento_date = agregar_dias_habiles(datetime.now().date(), data.dias_respuesta)
        vencimiento = datetime.combine(vencimiento_date, datetime.min.time())

        # 6. Guardar en Base de Datos
        cur.execute("""
            INSERT INTO radicados (
                nro_radicado, tipo_radicado, tipo_remitente, primer_apellido, segundo_apellido,
                nombre_razon_social, tipo_documento, nro_documento, cargo, direccion,
                telefono, correo_electronico, pais, departamento, ciudad,
                serie, subserie, tipo_documental, asunto, metodo_recepcion,
                nro_guia, nro_folios, dias_respuesta, fecha_vencimiento, anexo_nombre, descripcion_anexo,
                seccion_responsable, funcionario_responsable_id, con_copia, seccion_origen, funcionario_origen_id,
                path_principal, anexos_json, creado_por, estado
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
        """, (
            nro_radicado, data.tipo_radicado, data.tipo_remitente, data.primer_apellido, data.segundo_apellido,
            data.nombre_razon_social, data.tipo_documento, data.nro_documento, data.cargo, data.direccion,
            data.telefono, data.correo_electronico, data.pais, data.departamento, data.ciudad,
            data.serie, data.subserie, data.tipo_documental, data.asunto, data.metodo_recepcion,
            data.nro_guia, data.nro_folios, data.dias_respuesta, vencimiento.date(), data.anexo_nombre, data.descripcion_anexo,
            data.seccion_responsable, data.funcionario_responsable_id, data.con_copia, data.seccion_origen, data.funcionario_origen_id,
            path_p, json.dumps(rutas_anexos), user_info['id'], 'Radicado'
        ))

        # Primera entrada de trazabilidad: creación
        cur.execute("""
            INSERT INTO trazabilidad_radicados (nro_radicado, accion, comentario, desde_usuario_id, hacia_usuario_id, estado_nuevo)
            VALUES (?, 'CREACION', 'Radicado creado en ventanilla.', ?, ?, 'Radicado')
        """, (nro_radicado, user_info['id'], data.funcionario_responsable_id))

        # Notificar al responsable si es diferente al creador
        if data.funcionario_responsable_id and data.funcionario_responsable_id != user_info['id']:
            cur.execute("""
                INSERT INTO notificaciones (usuario_id, nro_radicado, mensaje)
                VALUES (?, ?, ?)
            """, (data.funcionario_responsable_id, nro_radicado, f"Nuevo documento recibido: {nro_radicado}"))

        conn.commit()
        registrar_evento(user_info['id'], 'RADICACION_OFICIAL', 'VENTANILLA', f"Generado: {nro_radicado}", request)
        
        return {"status": "success", "numero": nro_radicado, "vencimiento": str(vencimiento.date())}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close(); conn.close()

# --- 9. ADMINISTRACIÓN Y CONTROL DE EQUIPOS ---

@app.post("/admin/crear-usuario")
async def crear_usuario(request: Request, data: UserCreate, admin_info: dict = Depends(obtener_admin_actual)):
    # VALIDACIÓN DE SEGURIDAD:
    # 1. Nadie puede crear un Super Usuario (ID 0) por API
    if data.rol_id == 0:
        raise HTTPException(status_code=403, detail="No se permite la creación de Super Usuarios adicionales.")
    
    # 2. Solo el Super Usuario (Rol 0) puede crear Administradores (Rol 1)
    if data.rol_id == 1 and admin_info['rol'] != 0:
        registrar_evento(admin_info['id'], 'SECURITY_VIOLATION', 'ADMIN', f"Intento fallido de crear Admin por {admin_info['usuario']}", request)
        raise HTTPException(status_code=403, detail="Permisos insuficientes: Solo el Super Usuario puede designar Administradores.")

    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Verificar si el nombre de usuario ya existe
        cur.execute("SELECT id FROM usuarios WHERE usuario = ?", (data.usuario,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="El ID de usuario ya está en uso.")

        # Preparar credenciales
        from app.core.crypto import cifrar_secret
        hashed_pw = pwd_context.hash(data.password)
        secret_2fa = pyotp.random_base32()
        secret_cifrado = cifrar_secret(secret_2fa)

        # Generar QR code en base64
        from io import BytesIO
        import base64 as b64mod
        uri = pyotp.totp.TOTP(secret_2fa).provisioning_uri(name=data.usuario, issuer_name="SIADE")
        qr_img = qrcode.make(uri)
        buf = BytesIO()
        qr_img.save(buf, format="PNG")
        qr_b64 = b64mod.b64encode(buf.getvalue()).decode()

        # Insertar en la base de datos
        cur.execute(
            """INSERT INTO usuarios (usuario, password_hash, nombre_completo, rol_id, secret_2fa, activo)
               VALUES (?, ?, ?, ?, ?, TRUE)""",
            (data.usuario, hashed_pw, data.nombre_completo, data.rol_id, secret_cifrado)
        )
        nuevo_id = cur.lastrowid
        conn.commit()

        registrar_evento(admin_info['id'], 'CREATE_USER', 'ADMIN', f"Nuevo funcionario: {data.usuario} (Rol: {data.rol_id})", request)

        return {
            "status": "success",
            "message": "Usuario creado. Comparte la información de acceso con el funcionario.",
            "secret_2fa": secret_2fa,
            "qr_code": f"data:image/png;base64,{qr_b64}",
            "aviso": "El usuario deberá escanear el QR con Google Authenticator antes de su primer ingreso."
        }

    except Exception as e:
        conn.rollback()
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
    finally:
        cur.close(); conn.close()
        
@app.post("/admin/crear-equipo")
async def crear_equipo(request: Request, data: EquipoCreate, admin_info: dict = Depends(obtener_admin_actual)):
    nombre_limpio = data.nombre.strip()
    
    if not nombre_limpio:
        raise HTTPException(status_code=400, detail="El nombre del grupo no puede estar vacío")

    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # VALIDACIÓN: No permitir nombres iguales (ignora mayúsculas/minúsculas)
        cur.execute("SELECT id FROM equipos WHERE nombre LIKE ?", (nombre_limpio,))
        if cur.fetchone():
            cur.close(); conn.close()
            raise HTTPException(status_code=400, detail=f"El grupo '{nombre_limpio}' ya existe en SIADE.")

        # Inserción
        cur.execute("INSERT INTO equipos (nombre) VALUES (?)", (nombre_limpio,))
        equipo_id = cur.lastrowid
        conn.commit()
        
        registrar_evento(admin_info['id'], 'CREATE_TEAM', 'ADMIN', f"Nuevo grupo: {nombre_limpio}", request)
        return {"status": "success", "id": equipo_id, "message": "Grupo creado exitosamente"}
        
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error en base de datos: {str(e)}")
    finally:
        cur.close(); conn.close()

@app.get("/admin/listar-equipos")
async def listar_equipos(admin_info: dict = Depends(obtener_admin_actual)):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, nombre FROM equipos ORDER BY nombre ASC")
        res = cur.fetchall()
        return [dict(r) for r in res]
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error al listar grupos")
    finally:
        cur.close(); conn.close()

@app.post("/admin/asignar-equipos-usuario")
async def asignar_equipos(request: Request, data: AsignacionEquipos, admin_info: dict = Depends(obtener_admin_actual)):
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # LOGICA MASIVA: 
        # 1. Borramos usando '?' en lugar de '%s'
        cur.execute("DELETE FROM usuario_equipo WHERE usuario_id = ?", (data.usuario_id,))
        
        # 2. Insertamos las nuevas
        if data.equipos_ids:
            for eid in data.equipos_ids:
                # Cambiamos (%s, %s) por (?, ?)
                cur.execute("INSERT INTO usuario_equipo (usuario_id, equipo_id) VALUES (?, ?)", 
                           (data.usuario_id, eid))
        
        conn.commit()
        registrar_evento(admin_info['id'], 'ASSIGN_TEAM', 'ADMIN', f"Sincronización masiva de equipos para User ID: {data.usuario_id}", request)
        return {"status": "success", "message": "Equipos actualizados correctamente"}
        
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close(); conn.close()

# --- 10. CONFIGURACIÓN Y ESTADO ---

@app.post("/admin/cambiar-estado-usuario")
async def cambiar_estado_usuario(request: Request, data: UserStatusUpdate, admin_info: dict = Depends(obtener_admin_actual)):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute("UPDATE usuarios SET activo = ? WHERE id = ?", (data.nuevo_estado, data.user_id))
    conn.commit()
    registrar_evento(admin_info['id'], 'USER_STATUS_CHANGE', 'ADMIN', f"ID: {data.user_id}", request)
    cur.close(); conn.close(); return {"status": "success"}

@app.post("/admin/registrar-dependencia")
async def registrar_dependencia(request: Request, data: DependenciaCreate, admin_info: dict = Depends(obtener_admin_actual)):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO estructura_organica (entidad, unidad, oficina, depende_de) VALUES (?, ?, ?, ?)",
                (data.entidad, data.unidad_administrativa, data.oficina_productora, data.relacion_jerarquica))
    conn.commit(); registrar_evento(admin_info['id'], 'CONFIG_ESTRUCTURA', 'ADMIN', f"Nueva: {data.oficina_productora}", request)
    cur.close(); conn.close(); return {"status": "success"}

@app.post("/admin/registrar-trd")
async def registrar_trd(request: Request, data: TRDCreate, admin_info: dict = Depends(obtener_admin_actual)):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Usamos los nombres exactos que verificamos en tu consola SQL
        cur.execute("""
            INSERT INTO trd (
                cod_unidad, unidad, cod_oficina, oficina, 
                cod_serie, nombre_serie, cod_subserie, nombre_subserie, 
                tipo_documental, soporte, extension, años_gestion, 
                años_central, disposicion_final, porcentaje_seleccion, procedimiento
            ) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.cod_unidad, data.unidad, data.cod_oficina, data.oficina,
            data.cod_serie, data.nombre_serie, data.cod_subserie, data.nombre_subserie,
            data.tipo_documental, data.soporte, data.extension, data.años_gestion,
            data.años_central, data.disposicion_final, data.porcentaje_seleccion, data.procedimiento
        ))
        
        conn.commit()
        registrar_evento(admin_info['id'], 'CONFIG_TRD', 'ADMIN', f"Serie guardada: {data.nombre_serie}", request)
        return {"status": "success", "message": "Serie documental registrada exitosamente"}
        
    except Exception as e:
        conn.rollback()
        print(f"Error al insertar en TRD: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno al guardar: {str(e)}")
    finally:
        cur.close(); conn.close()

@app.get("/admin/descargar-plantilla-trd")
async def descargar_plantilla_trd():
    # Buscamos la ruta del archivo en la carpeta storage
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(BASE_DIR, "..", "storage", "plantilla_trd.xlsx")
    
    # Verificamos si el archivo realmente existe para no dar error 500
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="La plantilla no se encuentra en el servidor.")
    
    # Retornamos el archivo para que el navegador lo descargue
    return FileResponse(
        path=file_path, 
        filename="Plantilla_Oficial_TRD_SIADE.xlsx",
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

# --- 9. CARGA MASIVA (EXCEL) ---

@app.post("/admin/importar-trd-excel")
async def importar_trd_excel(request: Request, file: UploadFile = File(...), admin_info: dict = Depends(obtener_admin_actual)):
    try:
        content = await file.read()
        # Intentamos leer la hoja 'datos'
        df = pd.read_excel(BytesIO(content), sheet_name='datos')
        
        # DEBUG: Esto imprimirá en tu consola qué columnas está viendo Python
        print(f"Columnas detectadas en el Excel: {df.columns.tolist()}")

        conn = get_db_connection()
        cur = conn.cursor()
        count = 0
        
        for _, row in df.iterrows():
            # Usamos .get() con un valor por defecto para que no estalle si falta una columna
            cur.execute("""
                INSERT INTO trd (
                    cod_unidad, unidad, cod_oficina, oficina, 
                    cod_serie, nombre_serie, cod_subserie, nombre_subserie, 
                    tipo_documental, soporte, extension, años_gestion, 
                    años_central, disposicion_final, porcentaje_seleccion, procedimiento
                ) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(row.get('CodigoUnidad', '')),
                str(row.get('Unidad', '')),
                str(row.get('CodigoOficina', '')),
                str(row.get('Oficina', '')),
                str(row.get('CodigoSerie', '')),
                str(row.get('Serie', '')),
                str(row.get('CodigoSubserie', '')),
                str(row.get('Subserie', '')),
                str(row.get('TipoDocumental', '')),
                str(row.get('Soporte', 'Digital')),
                str(row.get('Extension', 'PDF')),
                int(row.get('Gestion', 0)) if row.get('Gestion') else 0,
                int(row.get('Central', 0)) if row.get('Central') else 0,
                str(row.get('Disposicion', 'Conservación Total')),
                int(row.get('Seleccion', 0)) if row.get('Seleccion') else 0,
                str(row.get('Procedimiento', ''))
            ))
            count += 1
            
        conn.commit()
        cur.close(); conn.close()
        return {"status": "success", "count": count}
    except Exception as e:
        # Esto te dirá el error real en el mensaje del navegador
        print(f"ERROR DE IMPORTACIÓN: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")

@app.post("/admin/importar-estructura-excel")
async def importar_estructura_excel(request: Request, file: UploadFile = File(...), admin_info: dict = Depends(obtener_admin_actual)):
    try:
        df = pd.read_excel(BytesIO(await file.read()))
        conn = get_db_connection(); cur = conn.cursor(); count = 0
        for _, row in df.iterrows():
            cur.execute("INSERT INTO estructura_organica (entidad, unidad, oficina, depende_de) VALUES (?, ?, ?, ?)",
                        (str(row['Entidad']), str(row['Unidad']), str(row['Oficina']), str(row.get('DependeDe', 'Nivel Raíz'))))
            count += 1
        conn.commit(); cur.close(); conn.close(); return {"status": "success", "count": count}
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))

# --- 10. LISTADORES ---

@app.get("/admin/listar-estructura")
async def listar_estructura(admin_info: dict = Depends(obtener_admin_actual)):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute("SELECT unidad, oficina, depende_de FROM estructura_organica ORDER BY unidad ASC")
    res = cur.fetchall(); cur.close(); conn.close(); return [dict(r) for r in res]

@app.get("/admin/listar-trd")
async def listar_trd(admin_info: dict = Depends(obtener_admin_actual)):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Usamos comillas dobles para las columnas con 'ñ' por seguridad en SQLite
        # Y mantenemos los alias que tu Frontend de Angular ya está usando

        cur.execute("""
            SELECT 
                cod_serie AS codigo, 
                unidad, 
                oficina, 
                nombre_serie AS serie, 
                cod_subserie, 
                nombre_subserie AS subserie, 
                tipo_documental,
                soporte, 
                años_gestion AS ag, 
                años_central AS ac, 
                disposicion_final AS disposicion 
            FROM trd 
            ORDER BY cod_serie ASC
        """)
        
        res = cur.fetchall()
        # dict(r) funciona gracias a que pusimos conn.row_factory = sqlite3.Row
        return [dict(r) for r in res]
    except Exception as e:
        print(f"Error en listar_trd: {e}")
        raise HTTPException(status_code=500, detail=f"Error al consultar la TRD: {str(e)}")
    finally:
        cur.close(); conn.close()

@app.get("/admin/listar-usuarios")
async def listar_usuarios(admin_info: dict = Depends(obtener_admin_actual)):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute("SELECT id, usuario, nombre_completo, rol_id, activo FROM usuarios WHERE rol_id > ?", (admin_info['rol'],))
    usuarios = cur.fetchall(); cur.close(); conn.close(); return [dict(u) for u in usuarios]

@app.get("/admin/eventos-recientes")
async def obtener_eventos_recientes(admin_info: dict = Depends(obtener_admin_actual)):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute("""
        SELECT a.fecha_accion, a.accion, a.modulo, a.detalle, u.usuario 
        FROM auditoria a 
        LEFT JOIN usuarios u ON a.usuario_id = u.id 
        ORDER BY a.fecha_accion DESC 
        LIMIT 15
    """)
    eventos = cur.fetchall(); cur.close(); conn.close(); return [dict(e) for e in eventos]

# --- 11. RADICACIÓN Y PLANTILLAS ---

@app.get("/static/templates/{filename}")
async def descargar_plantilla(filename: str):
    # Seguridad: solo permitir nombres de archivo simples, sin rutas relativas
    safe_name = os.path.basename(filename)
    if safe_name != filename or ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Nombre de archivo no permitido.")
    path = os.path.join("static", "templates", safe_name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404)
    return FileResponse(path)


@app.get("/radicados")
async def listar_radicados(user_info: dict = Depends(obtener_usuario_actual)):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        es_admin = user_info['rol'] <= 1
        if es_admin:
            cur.execute("""
                SELECT r.nro_radicado, r.tipo_radicado, r.tipo_remitente, r.nombre_razon_social,
                       r.asunto, r.metodo_recepcion, r.serie, r.subserie, r.seccion_responsable,
                       r.fecha_vencimiento, r.nro_folios, r.creado_por, r.path_principal,
                       r.estado, r.funcionario_responsable_id,
                       r.nro_radicado_relacionado,
                       (SELECT nro_radicado FROM radicados r2
                        WHERE r2.nro_radicado_relacionado = r.nro_radicado LIMIT 1) AS nro_respuesta,
                       u.nombre_completo AS responsable_nombre,
                       r.rowid as id
                FROM radicados r
                LEFT JOIN usuarios u ON r.funcionario_responsable_id = u.id
                ORDER BY r.rowid DESC
            """)
        else:
            cur.execute("""
                SELECT r.nro_radicado, r.tipo_radicado, r.tipo_remitente, r.nombre_razon_social,
                       r.asunto, r.metodo_recepcion, r.serie, r.subserie, r.seccion_responsable,
                       r.fecha_vencimiento, r.nro_folios, r.creado_por, r.path_principal,
                       r.estado, r.funcionario_responsable_id,
                       r.nro_radicado_relacionado,
                       (SELECT nro_radicado FROM radicados r2
                        WHERE r2.nro_radicado_relacionado = r.nro_radicado LIMIT 1) AS nro_respuesta,
                       u.nombre_completo AS responsable_nombre,
                       r.rowid as id
                FROM radicados r
                LEFT JOIN usuarios u ON r.funcionario_responsable_id = u.id
                WHERE r.creado_por = ? OR r.funcionario_responsable_id = ?
                ORDER BY r.rowid DESC
            """, (user_info['id'], user_info['id']))
        rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        cur.close(); conn.close()


@app.get("/radicados/{nro_radicado}/documento")
async def ver_documento_radicado(nro_radicado: str, user_info: dict = Depends(obtener_usuario_actual)):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        if user_info['rol'] <= 1:
            cur.execute("SELECT path_principal FROM radicados WHERE nro_radicado = ?", (nro_radicado,))
        else:
            cur.execute("""
                SELECT path_principal FROM radicados
                WHERE nro_radicado = ? AND (creado_por = ? OR funcionario_responsable_id = ?)
            """, (nro_radicado, user_info['id'], user_info['id']))
        row = cur.fetchone()
    finally:
        cur.close(); conn.close()

    if not row or not row['path_principal']:
        raise HTTPException(status_code=404, detail="Documento no encontrado para este radicado.")

    file_path = row['path_principal']

    # Seguridad: verificar que el archivo esté dentro del directorio storage permitido
    storage_dir = os.path.realpath(UPLOAD_DIR)
    real_path = os.path.realpath(file_path)
    if not real_path.startswith(storage_dir):
        raise HTTPException(status_code=403, detail="Acceso al archivo no permitido.")

    if not os.path.exists(real_path):
        raise HTTPException(status_code=404, detail="El archivo ya no existe en el servidor.")

    # Descifrar si el archivo está cifrado (.enc)
    from fastapi.responses import Response
    if real_path.endswith(".enc"):
        from app.core.cifrado_docs import descifrar_archivo
        datos = descifrar_archivo(real_path)
        # Nombre original sin .enc
        filename = os.path.basename(real_path).replace(".enc", "")
        media_type = "application/pdf" if filename.endswith(".pdf") else "application/octet-stream"
        return Response(content=datos, media_type=media_type,
                        headers={"Content-Disposition": f"inline; filename={filename}"})

    filename = os.path.basename(real_path)
    media_type = "application/pdf" if filename.endswith(".pdf") else "application/octet-stream"
    return FileResponse(path=real_path, filename=filename, media_type=media_type)


# --- MODELOS PARA FLUJO ---
class TrasladoData(BaseModel):
    nuevo_responsable_id: int
    comentario: str = ""

class ArchivarData(BaseModel):
    comentario: str = ""


@app.post("/radicados/{nro_radicado}/trasladar")
async def trasladar_radicado(nro_radicado: str, data: TrasladoData, request: Request, user_info: dict = Depends(obtener_usuario_actual)):
    conn = get_db_connection(); cur = conn.cursor()
    try:
        # Verificar que el radicado existe y que el usuario tiene acceso
        cur.execute("SELECT funcionario_responsable_id, estado FROM radicados WHERE nro_radicado = ?", (nro_radicado,))
        rad = cur.fetchone()
        if not rad:
            raise HTTPException(status_code=404, detail="Radicado no encontrado.")
        if user_info['rol'] > 1 and rad['funcionario_responsable_id'] != user_info['id']:
            raise HTTPException(status_code=403, detail="Solo el responsable actual puede trasladar este documento.")

        # Verificar que el nuevo responsable existe
        cur.execute("SELECT id, nombre_completo FROM usuarios WHERE id = ? AND activo = 1", (data.nuevo_responsable_id,))
        nuevo_resp = cur.fetchone()
        if not nuevo_resp:
            raise HTTPException(status_code=404, detail="El funcionario destino no existe o está inactivo.")

        # Actualizar radicado
        cur.execute("""
            UPDATE radicados SET funcionario_responsable_id = ?, estado = 'En Trámite'
            WHERE nro_radicado = ?
        """, (data.nuevo_responsable_id, nro_radicado))

        # Registrar trazabilidad
        cur.execute("""
            INSERT INTO trazabilidad_radicados (nro_radicado, accion, comentario, desde_usuario_id, hacia_usuario_id, estado_nuevo)
            VALUES (?, 'TRASLADO', ?, ?, ?, 'En Trámite')
        """, (nro_radicado, data.comentario or "Sin comentario.", user_info['id'], data.nuevo_responsable_id))

        # Notificar al nuevo responsable
        cur.execute("""
            INSERT INTO notificaciones (usuario_id, nro_radicado, mensaje)
            VALUES (?, ?, ?)
        """, (data.nuevo_responsable_id, nro_radicado, f"Documento trasladado a tu responsabilidad: {nro_radicado}"))

        conn.commit()
        registrar_evento(user_info['id'], 'TRASLADO', 'GESTION', f"{nro_radicado} → User ID {data.nuevo_responsable_id}", request)
        return {"status": "success", "mensaje": f"Trasladado a {nuevo_resp['nombre_completo']}."}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback(); raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close(); conn.close()


@app.post("/radicados/{nro_radicado}/archivar")
async def archivar_radicado(nro_radicado: str, data: ArchivarData, request: Request, user_info: dict = Depends(obtener_usuario_actual)):
    conn = get_db_connection(); cur = conn.cursor()
    try:
        cur.execute("SELECT funcionario_responsable_id FROM radicados WHERE nro_radicado = ?", (nro_radicado,))
        rad = cur.fetchone()
        if not rad:
            raise HTTPException(status_code=404, detail="Radicado no encontrado.")
        if user_info['rol'] > 1 and rad['funcionario_responsable_id'] != user_info['id']:
            raise HTTPException(status_code=403, detail="Solo el responsable puede archivar este documento.")

        cur.execute("UPDATE radicados SET estado = 'Archivado' WHERE nro_radicado = ?", (nro_radicado,))
        cur.execute("""
            INSERT INTO trazabilidad_radicados (nro_radicado, accion, comentario, desde_usuario_id, hacia_usuario_id, estado_nuevo)
            VALUES (?, 'ARCHIVADO', ?, ?, NULL, 'Archivado')
        """, (nro_radicado, data.comentario or "Radicado archivado y finalizado.", user_info['id']))

        conn.commit()
        registrar_evento(user_info['id'], 'ARCHIVADO', 'GESTION', nro_radicado, request)
        return {"status": "success", "mensaje": "Radicado archivado correctamente."}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback(); raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close(); conn.close()


@app.get("/radicados/{nro_radicado}/historial")
async def historial_radicado(nro_radicado: str, user_info: dict = Depends(obtener_usuario_actual)):
    conn = get_db_connection(); cur = conn.cursor()
    try:
        cur.execute("""
            SELECT t.id, t.accion, t.comentario, t.estado_nuevo, t.fecha,
                   ud.nombre_completo AS desde_nombre, ud.usuario AS desde_usuario,
                   uh.nombre_completo AS hacia_nombre, uh.usuario AS hacia_usuario
            FROM trazabilidad_radicados t
            LEFT JOIN usuarios ud ON t.desde_usuario_id = ud.id
            LEFT JOIN usuarios uh ON t.hacia_usuario_id = uh.id
            WHERE t.nro_radicado = ?
            ORDER BY t.fecha ASC
        """, (nro_radicado,))
        return [dict(r) for r in cur.fetchall()]
    finally:
        cur.close(); conn.close()


FLUJO_MAP = {
    "RAD": {
        "archivo": "radicacion-entrada.bpmn",
        "pasos": ["inicio", "ventanillaRadica", "asignarDependencia", "dependenciaRevisa", "elaborarRespuesta", "notificarCiudadano", "finProceso"],
        "estados": {
            "Radicado":   {"actual": "asignarDependencia",  "completados": ["inicio", "ventanillaRadica"]},
            "Asignado":   {"actual": "dependenciaRevisa",   "completados": ["inicio", "ventanillaRadica", "asignarDependencia"]},
            "En trámite": {"actual": "dependenciaRevisa",   "completados": ["inicio", "ventanillaRadica", "asignarDependencia"]},
            "Respondido": {"actual": "notificarCiudadano",  "completados": ["inicio", "ventanillaRadica", "asignarDependencia", "dependenciaRevisa", "elaborarRespuesta"]},
            "Archivado":  {"actual": "finProceso",          "completados": ["inicio", "ventanillaRadica", "asignarDependencia", "dependenciaRevisa", "elaborarRespuesta", "notificarCiudadano", "finProceso"]},
        }
    },
    "ENV": {
        "archivo": "radicacion-salida.bpmn",
        "pasos": ["inicio", "jefeAprueba", "ventanillaRadica", "enviarCorreo", "enviarFisico", "archivar", "fin"],
        "estados": {
            "Radicado":   {"actual": "ventanillaRadica",  "completados": ["inicio", "jefeAprueba"]},
            "En trámite": {"actual": "enviarCorreo",      "completados": ["inicio", "jefeAprueba", "ventanillaRadica"]},
            "Respondido": {"actual": "archivar",          "completados": ["inicio", "jefeAprueba", "ventanillaRadica", "enviarCorreo", "enviarFisico"]},
            "Archivado":  {"actual": "fin",               "completados": ["inicio", "jefeAprueba", "ventanillaRadica", "enviarCorreo", "enviarFisico", "archivar", "fin"]},
        }
    },
    "INV": {
        "archivo": "comunicacion-interna.bpmn",
        "pasos": ["inicio", "jefeAprueba", "radicarInterno", "notificarDestinatario", "ejecutarAccion", "archivar", "fin"],
        "estados": {
            "Radicado":   {"actual": "notificarDestinatario", "completados": ["inicio", "jefeAprueba", "radicarInterno"]},
            "En trámite": {"actual": "ejecutarAccion",        "completados": ["inicio", "jefeAprueba", "radicarInterno", "notificarDestinatario"]},
            "Respondido": {"actual": "archivar",              "completados": ["inicio", "jefeAprueba", "radicarInterno", "notificarDestinatario", "ejecutarAccion"]},
            "Archivado":  {"actual": "fin",                   "completados": ["inicio", "jefeAprueba", "radicarInterno", "notificarDestinatario", "ejecutarAccion", "archivar", "fin"]},
        }
    },
}

@app.post("/workflows/start")
async def iniciar_workflow(nro_radicado: str = Form(...), admin_info: dict = Depends(obtener_admin_actual)):
    conn = get_db_connection(); cur = conn.cursor()
    try:
        cur.execute("SELECT nro_radicado, tipo_radicado, estado FROM radicados WHERE nro_radicado = ?", (nro_radicado,))
        rad = cur.fetchone()
        if not rad:
            raise HTTPException(status_code=404, detail="Radicado no encontrado")

        nro_prefijo = nro_radicado.split("-")[0] if "-" in nro_radicado else "RAD"
        flujo_config = FLUJO_MAP.get(nro_prefijo, FLUJO_MAP["RAD"])
        estado = rad["estado"] or "Radicado"
        estado_config = flujo_config["estados"].get(estado, flujo_config["estados"]["Radicado"])

        cur.execute("""
            INSERT OR REPLACE INTO workflow_instances (nro_radicado, tipo_flujo, paso_actual, pasos_completados, estado, iniciado_por)
            VALUES (?, ?, ?, ?, 'activo', ?)
        """, (nro_radicado, nro_prefijo, estado_config["actual"], json.dumps(estado_config["completados"]), admin_info["id"]))
        conn.commit()
        return {"status": "ok", "nro_radicado": nro_radicado, "paso_actual": estado_config["actual"]}
    finally:
        conn.close()


@app.post("/workflows/{nro_radicado}/complete-task")
async def completar_tarea(nro_radicado: str, user_info: dict = Depends(obtener_usuario_actual)):
    conn = get_db_connection(); cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM workflow_instances WHERE nro_radicado = ?", (nro_radicado,))
        wf = cur.fetchone()
        if not wf:
            raise HTTPException(status_code=404, detail="Instancia de workflow no encontrada")

        nro_prefijo = nro_radicado.split("-")[0] if "-" in nro_radicado else "RAD"
        flujo_config = FLUJO_MAP.get(nro_prefijo, FLUJO_MAP["RAD"])
        pasos = flujo_config["pasos"]
        completados = json.loads(wf["pasos_completados"])
        paso_actual = wf["paso_actual"]

        if paso_actual == "fin":
            return {"status": "completado", "mensaje": "El flujo ya está finalizado"}

        if paso_actual not in completados:
            completados.append(paso_actual)

        idx_actual = pasos.index(paso_actual) if paso_actual in pasos else -1
        siguiente = pasos[idx_actual + 1] if idx_actual + 1 < len(pasos) else "fin"

        # Mapear siguiente paso a estado del radicado
        estados_map = {"fin": "Archivado", "archivar": "Archivado",
                       "notificarCiudadano": "Respondido", "elaborarRespuesta": "Respondido",
                       "enviarCorreo": "Respondido", "enviarFisico": "Respondido",
                       "asignarDependencia": "Asignado", "revisionDependencia": "En trámite",
                       "ejecutarAccion": "En trámite", "notificarDestinatario": "En trámite"}
        nuevo_estado = estados_map.get(siguiente, "En trámite")

        cur.execute("""
            UPDATE workflow_instances SET paso_actual = ?, pasos_completados = ?,
            fecha_actualizacion = CURRENT_TIMESTAMP WHERE nro_radicado = ?
        """, (siguiente, json.dumps(completados), nro_radicado))
        cur.execute("UPDATE radicados SET estado = ? WHERE nro_radicado = ?", (nuevo_estado, nro_radicado))
        conn.commit()
        return {"status": "ok", "paso_anterior": paso_actual, "paso_actual": siguiente, "estado_radicado": nuevo_estado}
    finally:
        conn.close()


@app.get("/workflows/{nro_radicado}/state")
async def estado_workflow(nro_radicado: str, user_info: dict = Depends(obtener_usuario_actual)):
    conn = get_db_connection(); cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM workflow_instances WHERE nro_radicado = ?", (nro_radicado,))
        wf = cur.fetchone()
        if not wf:
            raise HTTPException(status_code=404, detail="Instancia de workflow no encontrada. Inicie el flujo primero.")
        nro_prefijo = nro_radicado.split("-")[0] if "-" in nro_radicado else "RAD"
        flujo_config = FLUJO_MAP.get(nro_prefijo, FLUJO_MAP["RAD"])
        return {
            "nro_radicado": nro_radicado,
            "tipo_flujo": wf["tipo_flujo"],
            "paso_actual": wf["paso_actual"],
            "pasos_completados": json.loads(wf["pasos_completados"]),
            "todos_los_pasos": flujo_config["pasos"],
            "estado": wf["estado"],
            "fecha_inicio": wf["fecha_inicio"],
            "fecha_actualizacion": wf["fecha_actualizacion"]
        }
    finally:
        conn.close()


@app.get("/radicados/{nro_radicado}/flujo")
async def endpoint_flujo(nro_radicado: str, user_info: dict = Depends(obtener_usuario_actual)):
    conn = get_db_connection(); cur = conn.cursor()
    try:
        cur.execute("SELECT nro_radicado, tipo_radicado, estado FROM radicados WHERE nro_radicado = ?", (nro_radicado,))
        rad = cur.fetchone()
        if not rad:
            raise HTTPException(status_code=404, detail="Radicado no encontrado")

        nro_prefijo = nro_radicado.split("-")[0] if "-" in nro_radicado else "RAD"
        flujo_config = FLUJO_MAP.get(nro_prefijo, FLUJO_MAP["RAD"])

        # Usar instancia real del workflow si existe
        cur.execute("SELECT paso_actual, pasos_completados FROM workflow_instances WHERE nro_radicado = ?", (nro_radicado,))
        wf = cur.fetchone()
        if wf:
            paso_actual = wf["paso_actual"]
            pasos_completados = json.loads(wf["pasos_completados"])
        else:
            # Fallback: calcular por estado del radicado
            estado = rad["estado"] or "Radicado"
            estado_config = flujo_config["estados"].get(estado, flujo_config["estados"]["Radicado"])
            paso_actual = estado_config["actual"]
            pasos_completados = estado_config["completados"]

        return {
            "nro_radicado": nro_radicado,
            "estado": rad["estado"],
            "archivo_bpmn": flujo_config["archivo"],
            "paso_actual": paso_actual,
            "pasos_completados": pasos_completados,
            "todos_los_pasos": flujo_config["pasos"],
            "tiene_instancia_real": wf is not None
        }
    finally:
        conn.close()


@app.get("/mis-notificaciones")
async def mis_notificaciones(user_info: dict = Depends(obtener_usuario_actual)):
    conn = get_db_connection(); cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, nro_radicado, mensaje, leida, fecha
            FROM notificaciones WHERE usuario_id = ?
            ORDER BY fecha DESC LIMIT 20
        """, (user_info['id'],))
        return [dict(r) for r in cur.fetchall()]
    finally:
        cur.close(); conn.close()


@app.post("/mis-notificaciones/{notif_id}/leer")
async def marcar_notificacion_leida(notif_id: int, user_info: dict = Depends(obtener_usuario_actual)):
    conn = get_db_connection(); cur = conn.cursor()
    try:
        cur.execute("UPDATE notificaciones SET leida = 1 WHERE id = ? AND usuario_id = ?", (notif_id, user_info['id']))
        conn.commit()
        return {"status": "ok"}
    finally:
        cur.close(); conn.close()


@app.get("/usuarios-activos")
async def listar_usuarios_activos(user_info: dict = Depends(obtener_usuario_actual)):
    conn = get_db_connection(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, nombre_completo, usuario FROM usuarios WHERE activo = 1 ORDER BY nombre_completo")
        return [dict(u) for u in cur.fetchall()]
    finally:
        cur.close(); conn.close()

# --- ARCHIVO CENTRAL ---

class TransferenciaData(BaseModel):
    caja: str = ""
    carpeta: str = ""
    folio_inicio: Optional[int] = None
    folio_fin: Optional[int] = None
    llaves_busqueda: str = ""
    observaciones: str = ""

@app.post("/radicados/{nro_radicado}/transferir-archivo")
async def transferir_a_archivo_central(nro_radicado: str, data: TransferenciaData, request: Request, user_info: dict = Depends(obtener_admin_actual)):
    conn = get_db_connection(); cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM radicados WHERE nro_radicado = ?", (nro_radicado,))
        rad = cur.fetchone()
        if not rad:
            raise HTTPException(status_code=404, detail="Radicado no encontrado.")
        if rad['estado'] != 'Archivado':
            raise HTTPException(status_code=400, detail="Solo se pueden transferir radicados con estado 'Archivado'.")

        # Obtener disposición final de la TRD si aplica
        cur.execute("SELECT disposicion_final FROM trd WHERE nombre_serie = ? LIMIT 1", (rad['serie'],))
        trd_row = cur.fetchone()
        disposicion = trd_row['disposicion_final'] if trd_row else 'Conservación Total'

        import datetime
        anio = datetime.datetime.now().year

        cur.execute("""
            INSERT OR REPLACE INTO archivo_central
            (nro_radicado, serie, subserie, tipo_documental, asunto, anio_produccion,
             caja, carpeta, folio_inicio, folio_fin, llaves_busqueda, observaciones,
             disposicion_final, path_principal, transferido_por)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            nro_radicado, rad['serie'], rad['subserie'], rad['tipo_documental'], rad['asunto'], anio,
            data.caja, data.carpeta, data.folio_inicio, data.folio_fin,
            data.llaves_busqueda, data.observaciones, disposicion, rad['path_principal'], user_info['id']
        ))

        cur.execute("UPDATE radicados SET estado = 'En Archivo Central' WHERE nro_radicado = ?", (nro_radicado,))
        cur.execute("""
            INSERT INTO trazabilidad_radicados (nro_radicado, accion, comentario, desde_usuario_id, estado_nuevo)
            VALUES (?, 'TRANSFERENCIA', ?, ?, 'En Archivo Central')
        """, (nro_radicado, f"Transferido a Archivo Central. Caja: {data.caja}, Carpeta: {data.carpeta}.", user_info['id']))

        conn.commit()
        registrar_evento(user_info['id'], 'TRANSFERENCIA_ARCHIVO', 'ARCHIVO_CENTRAL', nro_radicado, request)
        return {"status": "success", "mensaje": f"Radicado transferido al Archivo Central. Disposición: {disposicion}."}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback(); raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close(); conn.close()


@app.get("/radicados/{nro_radicado}/pdf-info")
async def info_pdf(nro_radicado: str, user_info: dict = Depends(obtener_usuario_actual)):
    """Retorna información del PDF (páginas, metadatos) sin descargarlo completo."""
    from app.core.pdf_utils import obtener_info_pdf
    from app.core.cifrado_docs import descifrar_archivo
    conn = get_db_connection(); cur = conn.cursor()
    try:
        cur.execute("SELECT path_principal, asunto, serie, subserie, nombre_razon_social FROM radicados WHERE nro_radicado = ?", (nro_radicado,))
        rad = cur.fetchone()
        if not rad or not rad["path_principal"]:
            raise HTTPException(status_code=404, detail="Documento no encontrado")
        path = rad["path_principal"]
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="Archivo no existe en el servidor")
        datos = descifrar_archivo(path) if path.endswith(".enc") else open(path, "rb").read()
        info = obtener_info_pdf(datos)
        info["nro_radicado"] = nro_radicado
        info["asunto"] = rad["asunto"]
        info["serie"] = rad["serie"]
        info["subserie"] = rad["subserie"]
        return info
    finally:
        conn.close()


@app.post("/radicados/{nro_radicado}/dividir-pdf")
async def dividir_pdf(
    nro_radicado: str,
    pagina_inicio: int = Form(1),
    pagina_fin: int = Form(0),
    modo: str = Form("rango"),
    user_info: dict = Depends(obtener_usuario_actual)
):
    """
    Divide el PDF de un radicado.
    modo='rango': extrae páginas pagina_inicio a pagina_fin
    modo='todas': retorna info de todas las páginas (no descarga individual)
    """
    from app.core.pdf_utils import dividir_pdf_por_rango, obtener_info_pdf
    from app.core.cifrado_docs import descifrar_archivo, cifrar_bytes
    from fastapi.responses import Response
    conn = get_db_connection(); cur = conn.cursor()
    try:
        cur.execute("""
            SELECT path_principal, asunto, serie, subserie, nombre_razon_social, nro_radicado
            FROM radicados WHERE nro_radicado = ?
        """, (nro_radicado,))
        rad = cur.fetchone()
        if not rad or not rad["path_principal"]:
            raise HTTPException(status_code=404, detail="Documento no encontrado")

        path = rad["path_principal"]
        datos = descifrar_archivo(path) if path.endswith(".enc") else open(path, "rb").read()

        meta = {
            "nro_radicado": nro_radicado,
            "asunto": rad["asunto"] or "",
            "serie": rad["serie"] or "",
            "subserie": rad["subserie"] or "",
            "nombre_razon_social": rad["nombre_razon_social"] or "",
        }

        if modo == "todas":
            info = obtener_info_pdf(datos)
            return {"nro_radicado": nro_radicado, **info}

        # Modo rango
        info = obtener_info_pdf(datos)
        fin = pagina_fin if pagina_fin > 0 else info["num_paginas"]
        resultado = dividir_pdf_por_rango(datos, pagina_inicio, fin, meta)

        # Guardar fragmento cifrado en storage
        nombre_fragmento = resultado["nombre"]
        path_fragmento = f"{UPLOAD_DIR}/{nombre_fragmento}.enc"
        with open(path_fragmento, "wb") as f:
            f.write(cifrar_bytes(resultado["bytes"]))

        registrar_evento(user_info['id'], 'DIVIDIR_PDF', 'GESTION',
                         f"Fragmento p{pagina_inicio}-{fin} de {nro_radicado}", None)

        return Response(
            content=resultado["bytes"],
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={nombre_fragmento}"}
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()


@app.get("/sla/semaforo/{nro_radicado}")
async def semaforo_radicado(nro_radicado: str, user_info: dict = Depends(obtener_usuario_actual)):
    from app.core.dias_habiles import calcular_semaforo
    conn = get_db_connection(); cur = conn.cursor()
    try:
        cur.execute("SELECT fecha_vencimiento, dias_respuesta FROM radicados WHERE nro_radicado = ?", (nro_radicado,))
        rad = cur.fetchone()
        if not rad or not rad["fecha_vencimiento"]:
            return {"color": "gris", "emoji": "⚪", "mensaje": "Sin fecha de vencimiento", "dias_restantes": None, "porcentaje_consumido": 0}
        from datetime import date
        fecha_venc = date.fromisoformat(str(rad["fecha_vencimiento"])[:10])
        dias_totales = rad["dias_respuesta"] or 15
        return calcular_semaforo(fecha_venc, dias_totales)
    finally:
        conn.close()


@app.get("/sla/festivos")
async def festivos_colombia(anio: int = 0, user_info: dict = Depends(obtener_usuario_actual)):
    from app.core.dias_habiles import festivos_anio
    from datetime import date
    anio_consulta = anio if anio > 0 else date.today().year
    return {"anio": anio_consulta, "festivos": festivos_anio(anio_consulta)}


@app.get("/sla/calcular-vencimiento")
async def calcular_vencimiento(fecha_inicio: str, dias_habiles: int = 15, user_info: dict = Depends(obtener_usuario_actual)):
    from app.core.dias_habiles import agregar_dias_habiles
    from datetime import date
    try:
        inicio = date.fromisoformat(fecha_inicio)
        vencimiento = agregar_dias_habiles(inicio, dias_habiles)
        return {
            "fecha_inicio": str(inicio),
            "dias_habiles": dias_habiles,
            "fecha_vencimiento": str(vencimiento),
            "nota": "Calculado con festivos colombianos incluidos"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/archivo-central")
async def consultar_archivo_central(
    q: str = "", anio: int = 0, serie: str = "", caja: str = "",
    disposicion: str = "", user_info: dict = Depends(obtener_usuario_actual)
):
    conn = get_db_connection(); cur = conn.cursor()
    try:
        filtros, params = [], []
        if q:
            filtros.append("(a.nro_radicado LIKE ? OR a.asunto LIKE ? OR a.llaves_busqueda LIKE ?)")
            params += [f"%{q}%", f"%{q}%", f"%{q}%"]
        if anio:
            filtros.append("a.anio_produccion = ?"); params.append(anio)
        if serie:
            filtros.append("a.serie LIKE ?"); params.append(f"%{serie}%")
        if caja:
            filtros.append("a.caja LIKE ?"); params.append(f"%{caja}%")
        if disposicion:
            filtros.append("a.disposicion_final = ?"); params.append(disposicion)

        where = ("WHERE " + " AND ".join(filtros)) if filtros else ""
        cur.execute(f"""
            SELECT a.*, u.nombre_completo AS transferido_por_nombre
            FROM archivo_central a
            LEFT JOIN usuarios u ON a.transferido_por = u.id
            {where}
            ORDER BY a.fecha_transferencia DESC
        """, params)
        return [dict(r) for r in cur.fetchall()]
    finally:
        cur.close(); conn.close()


# =====================================================================
# T4.5.1 / T4.5.2 — Facturas Electrónicas DIAN UBL 2.1
# =====================================================================

@app.post("/facturas/parsear-xml")
async def parsear_xml_dian(
    archivo: UploadFile = File(...),
    user_info: dict = Depends(obtener_usuario_actual)
):
    """
    T4.5.1 — Recibe un archivo XML de factura DIAN y retorna los datos parseados.
    No guarda nada en BD. Sirve como preview antes de radicar.
    """
    from app.core.dian_parser import parsear_factura_dian, validar_xml_dian

    contenido = await archivo.read()

    # Validar que sea XML y tenga estructura DIAN
    validacion = validar_xml_dian(contenido)

    # Intentar parsear (incluso con advertencias)
    try:
        datos = parsear_factura_dian(contenido)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al procesar el XML: {str(e)}")

    registrar_evento(
        user_info['id'], 'PARSEAR_XML_DIAN', 'FACTURAS',
        f"XML parseado: {datos.get('nro_factura','?')} — {datos.get('nombre_proveedor','?')}",
        None
    )

    return {
        "validacion": validacion,
        "datos": datos
    }


@app.post("/facturas/radicar-dian")
async def radicar_factura_dian(
    archivo: UploadFile = File(...),
    user_info: dict = Depends(obtener_usuario_actual)
):
    """
    T4.5.2 — Parsea el XML DIAN, guarda en facturas_dian y crea radicado automático.
    Retorna el nro_radicado generado.
    """
    from app.core.dian_parser import parsear_factura_dian, validar_xml_dian
    from app.core.cifrado_docs import cifrar_bytes
    from app.core.dias_habiles import agregar_dias_habiles
    from datetime import date

    contenido = await archivo.read()

    validacion = validar_xml_dian(contenido)
    if not validacion["valido"]:
        raise HTTPException(
            status_code=422,
            detail=f"XML DIAN inválido: {'; '.join(validacion['errores'])}"
        )

    try:
        datos = parsear_factura_dian(contenido)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    conn = get_db_connection(); cur = conn.cursor()
    try:
        # Verificar si ya existe la factura (por nro_factura o CUFE)
        cur.execute(
            "SELECT id, nro_radicado FROM facturas_dian WHERE nro_factura = ? OR (cufe != '' AND cufe = ?)",
            (datos["nro_factura"], datos["cufe"] or "")
        )
        existente = cur.fetchone()
        if existente:
            raise HTTPException(
                status_code=409,
                detail=f"La factura {datos['nro_factura']} ya fue registrada. "
                       f"Radicado: {existente['nro_radicado'] or 'sin radicado'}"
            )

        # --- Guardar XML cifrado en storage ---
        nombre_xml = f"DIAN_{datos['nro_factura'].replace('/', '-')}_{datos['nit_proveedor']}.xml.enc"
        path_xml = f"{UPLOAD_DIR}/{nombre_xml}"
        with open(path_xml, "wb") as f:
            f.write(cifrar_bytes(contenido))

        # --- Generar número de radicado (tipo ENTRADA) ---
        prefijo = "RE"
        anio = date.today().year
        cur.execute(
            "INSERT INTO secuencia_radicados (prefijo, anio, ultimo_numero) VALUES (?, ?, 1) "
            "ON CONFLICT(prefijo, anio) DO UPDATE SET ultimo_numero = ultimo_numero + 1",
            (prefijo, anio)
        )
        cur.execute("SELECT ultimo_numero FROM secuencia_radicados WHERE prefijo=? AND anio=?", (prefijo, anio))
        seq = cur.fetchone()["ultimo_numero"]
        nro_radicado = f"{prefijo}-{anio}-{seq:05d}"

        # --- Fecha de vencimiento (15 días hábiles) ---
        try:
            fecha_emision = date.fromisoformat(datos["fecha_emision"]) if datos["fecha_emision"] else date.today()
        except Exception:
            fecha_emision = date.today()
        fecha_vencimiento = agregar_dias_habiles(fecha_emision, 15)

        # --- Insertar radicado automático ---
        cur.execute("""
            INSERT INTO radicados (
                nro_radicado, tipo_radicado, tipo_remitente,
                nombre_razon_social, nro_documento,
                correo_electronico, telefono, direccion, ciudad,
                serie, subserie, tipo_documental,
                asunto, metodo_recepcion,
                dias_respuesta, fecha_vencimiento,
                path_principal, creado_por
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            nro_radicado, "Entrada", "Jurídica",
            datos["nombre_proveedor"], datos["nit_proveedor"],
            datos["correo_proveedor"], datos["telefono_proveedor"],
            datos["direccion_proveedor"], datos["ciudad_proveedor"],
            datos["serie_sugerida"], datos["subserie_sugerida"], "Factura Electrónica",
            datos["asunto_radicacion"], "Digital (DIAN)",
            15, str(fecha_vencimiento),
            path_xml, user_info["id"]
        ))

        # --- Insertar en facturas_dian ---
        cur.execute("""
            INSERT INTO facturas_dian (
                nro_radicado, tipo_documento, nro_factura, cufe,
                fecha_emision, nit_proveedor, nombre_proveedor,
                correo_proveedor, telefono_proveedor, direccion_proveedor, ciudad_proveedor,
                nit_receptor, nombre_receptor,
                valor_bruto, descuentos, iva, valor_a_pagar,
                moneda, forma_pago, fecha_vence_pago,
                items_json, path_xml, radicado_automatico, estado, creado_por
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 'radicada', ?)
        """, (
            nro_radicado, datos["tipo_documento"], datos["nro_factura"], datos["cufe"],
            datos["fecha_emision"], datos["nit_proveedor"], datos["nombre_proveedor"],
            datos["correo_proveedor"], datos["telefono_proveedor"],
            datos["direccion_proveedor"], datos["ciudad_proveedor"],
            datos["nit_receptor"], datos["nombre_receptor"],
            datos["valor_bruto"], datos["descuentos"], datos["iva"], datos["valor_a_pagar"],
            datos["moneda"], datos["forma_pago"], datos["fecha_vence_pago"],
            json.dumps(datos["items"], ensure_ascii=False),
            path_xml, user_info["id"]
        ))

        conn.commit()

        registrar_evento(
            user_info['id'], 'RADICAR_FACTURA_DIAN', 'FACTURAS',
            f"Radicación automática: {nro_radicado} — Factura {datos['nro_factura']} de {datos['nombre_proveedor']}",
            None
        )

        return {
            "ok": True,
            "nro_radicado": nro_radicado,
            "nro_factura": datos["nro_factura"],
            "proveedor": datos["nombre_proveedor"],
            "valor_a_pagar": datos["valor_a_pagar"],
            "fecha_vencimiento": str(fecha_vencimiento),
            "mensaje": f"Factura radicada automáticamente como {nro_radicado}"
        }

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
    finally:
        conn.close()


@app.get("/facturas/dian")
async def listar_facturas_dian(
    q: str = "",
    estado: str = "",
    page: int = 1,
    per_page: int = 20,
    user_info: dict = Depends(obtener_usuario_actual)
):
    """Lista las facturas DIAN registradas con filtros y paginación."""
    conn = get_db_connection(); cur = conn.cursor()
    try:
        filtros, params = [], []
        if q:
            filtros.append("(f.nro_factura LIKE ? OR f.nombre_proveedor LIKE ? OR f.nro_radicado LIKE ? OR f.cufe LIKE ?)")
            params += [f"%{q}%"] * 4
        if estado:
            filtros.append("f.estado = ?"); params.append(estado)
        where = ("WHERE " + " AND ".join(filtros)) if filtros else ""
        offset = (page - 1) * per_page

        cur.execute(f"SELECT COUNT(*) as total FROM facturas_dian f {where}", params)
        total = cur.fetchone()["total"]

        cur.execute(f"""
            SELECT f.*, u.nombre_completo AS registrado_por_nombre
            FROM facturas_dian f
            LEFT JOIN usuarios u ON f.creado_por = u.id
            {where}
            ORDER BY f.fecha_registro DESC
            LIMIT ? OFFSET ?
        """, params + [per_page, offset])

        return {
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": max(1, -(-total // per_page)),
            "facturas": [dict(r) for r in cur.fetchall()]
        }
    finally:
        conn.close()


@app.get("/facturas/dian/{id}")
async def detalle_factura_dian(id: int, user_info: dict = Depends(obtener_usuario_actual)):
    """Retorna el detalle completo de una factura DIAN incluyendo sus ítems."""
    conn = get_db_connection(); cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM facturas_dian WHERE id = ?", (id,))
        f = cur.fetchone()
        if not f:
            raise HTTPException(status_code=404, detail="Factura no encontrada")
        result = dict(f)
        if result.get("items_json"):
            try:
                result["items"] = json.loads(result["items_json"])
            except Exception:
                result["items"] = []
        return result
    finally:
        conn.close()
