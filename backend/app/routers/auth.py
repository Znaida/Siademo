import os
import random
import pyotp
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Request, Form
from jose import jwt
from app.core.config import SECRET_KEY, ALGORITHM, pwd_context
from app.core.database import get_db_connection
from app.core.security import firmar_resultado, verificar_password, registrar_evento

router = APIRouter()


@router.post("/admin/setup")
async def setup_inicial():
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
            raise HTTPException(status_code=500, detail="Variables ADMIN_USER y ADMIN_PASS no están configuradas.")

        password_hash = pwd_context.hash(admin_pass)
        secret_2fa = pyotp.random_base32()

        cur.execute(
            "INSERT INTO usuarios (usuario, password_hash, nombre_completo, rol_id, secret_2fa, activo) VALUES (?, ?, ?, 0, ?, 1)",
            (admin_user, password_hash, admin_name, secret_2fa)
        )
        conn.commit()
        return {
            "mensaje": "✅ Administrador creado exitosamente",
            "usuario": admin_user,
            "nombre": admin_name,
            "secret_2fa": secret_2fa,
            "tip": "Abre Google Authenticator → Agregar cuenta → Ingresar clave → pega el secret_2fa"
        }
    finally:
        cur.close()
        conn.close()


@router.get("/auth/captcha")
def generar_captcha():
    num1 = random.randint(1, 10)
    num2 = random.randint(1, 10)
    resultado = num1 + num2
    return {"pregunta": f"{num1} + {num2}", "captcha_token": firmar_resultado(resultado)}


@router.post("/auth/login")
async def login(
    request: Request,
    usuario: str = Form(...),
    password: str = Form(...),
    captcha_res: int = Form(...),
    captcha_token: str = Form(...)
):
    if firmar_resultado(captcha_res) != captcha_token:
        raise HTTPException(status_code=401, detail="Captcha incorrecto")

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, password_hash, rol_id FROM usuarios WHERE usuario = ? AND activo = TRUE", (usuario,))
    user = cur.fetchone()

    if not user or not verificar_password(password, user['password_hash']):
        registrar_evento(None, 'LOGIN_FAILED', 'AUTH', f'Fallo: {usuario}', request)
        raise HTTPException(status_code=401, detail="Usuario inactivo o credenciales inválidas")

    registrar_evento(user['id'], 'LOGIN_PASO_1', 'AUTH', 'Acceso paso 1', request)
    cur.close()
    conn.close()
    return {"status": "success", "usuario": usuario}


@router.post("/auth/verify-2fa")
async def verify_2fa(request: Request, usuario: str = Form(...), codigo: str = Form(...)):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, secret_2fa, rol_id FROM usuarios WHERE usuario = ?", (usuario,))
    user = cur.fetchone()
    secret = user['secret_2fa'] if user['secret_2fa'] else "JBSWY3DPEHPK3PXP"
    totp = pyotp.TOTP(secret)
    if totp.verify(codigo):
        token_data = {
            "sub": usuario,
            "id_usuario": user['id'],
            "rol": user['rol_id'],
            "exp": datetime.utcnow() + timedelta(hours=8)
        }
        token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
        registrar_evento(user['id'], 'LOGIN_SUCCESS', 'AUTH', 'Sesión iniciada', request)
        return {"access_token": token, "token_type": "bearer", "rol": user['rol_id']}
    else:
        raise HTTPException(status_code=401, detail="TOTP inválido")
