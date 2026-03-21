import os
from io import BytesIO
from typing import List
import pandas as pd
import pyotp
from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Depends
from fastapi.responses import FileResponse
from app.core.config import pwd_context
from app.core.database import get_db_connection
from app.core.security import obtener_admin_actual, registrar_evento
from app.schemas.usuario import UserCreate, UserStatusUpdate
from app.schemas.admin import DependenciaCreate, TRDCreate, EquipoCreate, AsignacionEquipos

router = APIRouter(prefix="/admin")


@router.post("/crear-usuario")
async def crear_usuario(request: Request, data: UserCreate, admin_info: dict = Depends(obtener_admin_actual)):
    if data.rol_id == 0:
        raise HTTPException(status_code=403, detail="No se permite la creación de Super Usuarios adicionales.")
    if data.rol_id == 1 and admin_info['rol'] != 0:
        registrar_evento(admin_info['id'], 'SECURITY_VIOLATION', 'ADMIN', f"Intento fallido de crear Admin por {admin_info['usuario']}", request)
        raise HTTPException(status_code=403, detail="Permisos insuficientes.")

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM usuarios WHERE usuario = ?", (data.usuario,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="El ID de usuario ya está en uso.")

        hashed_pw = pwd_context.hash(data.password)
        secret_2fa = pyotp.random_base32()

        cur.execute(
            "INSERT INTO usuarios (usuario, password_hash, nombre_completo, rol_id, secret_2fa, activo) VALUES (?, ?, ?, ?, ?, TRUE)",
            (data.usuario, hashed_pw, data.nombre_completo, data.rol_id, secret_2fa)
        )
        conn.commit()
        registrar_evento(admin_info['id'], 'CREATE_USER', 'ADMIN', f"Nuevo funcionario: {data.usuario} (Rol: {data.rol_id})", request)
        return {"status": "success", "message": "Usuario creado correctamente", "secret_2fa": secret_2fa}
    except Exception as e:
        conn.rollback()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
    finally:
        cur.close()
        conn.close()


@router.post("/crear-equipo")
async def crear_equipo(request: Request, data: EquipoCreate, admin_info: dict = Depends(obtener_admin_actual)):
    nombre_limpio = data.nombre.strip()
    if not nombre_limpio:
        raise HTTPException(status_code=400, detail="El nombre del grupo no puede estar vacío")

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM equipos WHERE nombre LIKE ?", (nombre_limpio,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail=f"El grupo '{nombre_limpio}' ya existe.")

        cur.execute("INSERT INTO equipos (nombre) VALUES (?)", (nombre_limpio,))
        equipo_id = cur.lastrowid
        conn.commit()
        registrar_evento(admin_info['id'], 'CREATE_TEAM', 'ADMIN', f"Nuevo grupo: {nombre_limpio}", request)
        return {"status": "success", "id": equipo_id, "message": "Grupo creado exitosamente"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


@router.get("/listar-equipos")
async def listar_equipos(admin_info: dict = Depends(obtener_admin_actual)):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, nombre FROM equipos ORDER BY nombre ASC")
        return [dict(r) for r in cur.fetchall()]
    finally:
        cur.close()
        conn.close()


@router.post("/asignar-equipos-usuario")
async def asignar_equipos(request: Request, data: AsignacionEquipos, admin_info: dict = Depends(obtener_admin_actual)):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM usuario_equipo WHERE usuario_id = ?", (data.usuario_id,))
        for eid in data.equipos_ids:
            cur.execute("INSERT INTO usuario_equipo (usuario_id, equipo_id) VALUES (?, ?)", (data.usuario_id, eid))
        conn.commit()
        registrar_evento(admin_info['id'], 'ASSIGN_TEAM', 'ADMIN', f"Equipos para User ID: {data.usuario_id}", request)
        return {"status": "success", "message": "Equipos actualizados correctamente"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


@router.post("/cambiar-estado-usuario")
async def cambiar_estado_usuario(request: Request, data: UserStatusUpdate, admin_info: dict = Depends(obtener_admin_actual)):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE usuarios SET activo = ? WHERE id = ?", (data.nuevo_estado, data.user_id))
    conn.commit()
    registrar_evento(admin_info['id'], 'USER_STATUS_CHANGE', 'ADMIN', f"ID: {data.user_id}", request)
    cur.close()
    conn.close()
    return {"status": "success"}


@router.post("/registrar-dependencia")
async def registrar_dependencia(request: Request, data: DependenciaCreate, admin_info: dict = Depends(obtener_admin_actual)):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO estructura_organica (entidad, unidad, oficina, depende_de) VALUES (?, ?, ?, ?)",
                (data.entidad, data.unidad_administrativa, data.oficina_productora, data.relacion_jerarquica))
    conn.commit()
    registrar_evento(admin_info['id'], 'CONFIG_ESTRUCTURA', 'ADMIN', f"Nueva: {data.oficina_productora}", request)
    cur.close()
    conn.close()
    return {"status": "success"}


@router.post("/registrar-trd")
async def registrar_trd(request: Request, data: TRDCreate, admin_info: dict = Depends(obtener_admin_actual)):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO trd (cod_unidad, unidad, cod_oficina, oficina, cod_serie, nombre_serie,
                cod_subserie, nombre_subserie, tipo_documental, soporte, extension,
                años_gestion, años_central, disposicion_final, porcentaje_seleccion, procedimiento)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (data.cod_unidad, data.unidad, data.cod_oficina, data.oficina, data.cod_serie, data.nombre_serie,
              data.cod_subserie, data.nombre_subserie, data.tipo_documental, data.soporte, data.extension,
              data.años_gestion, data.años_central, data.disposicion_final, data.porcentaje_seleccion, data.procedimiento))
        conn.commit()
        registrar_evento(admin_info['id'], 'CONFIG_TRD', 'ADMIN', f"Serie guardada: {data.nombre_serie}", request)
        return {"status": "success", "message": "Serie documental registrada exitosamente"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


@router.get("/descargar-plantilla-trd")
async def descargar_plantilla_trd():
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    file_path = os.path.join(BASE_DIR, "..", "storage", "plantilla_trd.xlsx")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="La plantilla no se encuentra en el servidor.")
    return FileResponse(path=file_path, filename="Plantilla_Oficial_TRD_SIADE.xlsx",
                        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@router.post("/importar-trd-excel")
async def importar_trd_excel(request: Request, file: UploadFile = File(...), admin_info: dict = Depends(obtener_admin_actual)):
    try:
        df = pd.read_excel(BytesIO(await file.read()), sheet_name='datos')
        conn = get_db_connection()
        cur = conn.cursor()
        count = 0
        for _, row in df.iterrows():
            cur.execute("""
                INSERT INTO trd (cod_unidad, unidad, cod_oficina, oficina, cod_serie, nombre_serie,
                    cod_subserie, nombre_subserie, tipo_documental, soporte, extension,
                    años_gestion, años_central, disposicion_final, porcentaje_seleccion, procedimiento)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (str(row.get('CodigoUnidad', '')), str(row.get('Unidad', '')),
                  str(row.get('CodigoOficina', '')), str(row.get('Oficina', '')),
                  str(row.get('CodigoSerie', '')), str(row.get('Serie', '')),
                  str(row.get('CodigoSubserie', '')), str(row.get('Subserie', '')),
                  str(row.get('TipoDocumental', '')), str(row.get('Soporte', 'Digital')),
                  str(row.get('Extension', 'PDF')),
                  int(row.get('Gestion', 0)) if row.get('Gestion') else 0,
                  int(row.get('Central', 0)) if row.get('Central') else 0,
                  str(row.get('Disposicion', 'Conservación Total')),
                  int(row.get('Seleccion', 0)) if row.get('Seleccion') else 0,
                  str(row.get('Procedimiento', ''))))
            count += 1
        conn.commit()
        cur.close()
        conn.close()
        return {"status": "success", "count": count}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/importar-estructura-excel")
async def importar_estructura_excel(request: Request, file: UploadFile = File(...), admin_info: dict = Depends(obtener_admin_actual)):
    try:
        df = pd.read_excel(BytesIO(await file.read()))
        conn = get_db_connection()
        cur = conn.cursor()
        count = 0
        for _, row in df.iterrows():
            cur.execute("INSERT INTO estructura_organica (entidad, unidad, oficina, depende_de) VALUES (?, ?, ?, ?)",
                        (str(row['Entidad']), str(row['Unidad']), str(row['Oficina']), str(row.get('DependeDe', 'Nivel Raíz'))))
            count += 1
        conn.commit()
        cur.close()
        conn.close()
        return {"status": "success", "count": count}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/listar-estructura")
async def listar_estructura(admin_info: dict = Depends(obtener_admin_actual)):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT unidad, oficina, depende_de FROM estructura_organica ORDER BY unidad ASC")
    res = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in res]


@router.get("/listar-trd")
async def listar_trd(admin_info: dict = Depends(obtener_admin_actual)):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT cod_serie AS codigo, unidad, oficina, nombre_serie AS serie,
                   cod_subserie, nombre_subserie AS subserie, tipo_documental, soporte,
                   años_gestion AS ag, años_central AS ac, disposicion_final AS disposicion
            FROM trd ORDER BY cod_serie ASC
        """)
        return [dict(r) for r in cur.fetchall()]
    finally:
        cur.close()
        conn.close()


@router.get("/listar-usuarios")
async def listar_usuarios(admin_info: dict = Depends(obtener_admin_actual)):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, usuario, nombre_completo, rol_id, activo FROM usuarios WHERE rol_id > ?", (admin_info['rol'],))
    usuarios = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(u) for u in usuarios]


@router.get("/eventos-recientes")
async def obtener_eventos_recientes(admin_info: dict = Depends(obtener_admin_actual)):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT a.fecha_accion, a.accion, a.modulo, a.detalle, u.usuario
        FROM auditoria a LEFT JOIN usuarios u ON a.usuario_id = u.id
        ORDER BY a.fecha_accion DESC LIMIT 15
    """)
    eventos = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(e) for e in eventos]
