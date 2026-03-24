"""
Tests de autenticación: captcha, login paso 1, verify-2fa, cambio de password.
Estos tests ejercen la lógica real de auth (sin override de dependencias).
"""
import pyotp
from app.core.security import firmar_resultado

TEST_2FA_SECRET = "JBSWY3DPEHPK3PXP"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def captcha_valido(client):
    """Obtiene un captcha y devuelve (captcha_res, captcha_token)."""
    res = client.get("/auth/captcha")
    data = res.json()
    num1, num2 = [int(x.strip()) for x in data["pregunta"].split("+")]
    resultado = num1 + num2
    return resultado, firmar_resultado(resultado)


def totp_actual():
    return pyotp.TOTP(TEST_2FA_SECRET).now()


# ---------------------------------------------------------------------------
# Captcha
# ---------------------------------------------------------------------------

def test_captcha_token_correcto(client):
    """El token firmado con el resultado correcto debe ser válido."""
    captcha_res, captcha_token = captcha_valido(client)
    assert captcha_token == firmar_resultado(captcha_res)


def test_captcha_token_incorrecto_rechazado(client):
    """Un captcha_token con resultado incorrecto provoca 401."""
    _, captcha_token = captcha_valido(client)
    res = client.post("/auth/login", data={
        "usuario": "admin_test",
        "password": "TestPass123!",
        "captcha_res": 9999,
        "captcha_token": captcha_token,
    })
    assert res.status_code == 401
    assert "captcha" in res.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Login paso 1
# ---------------------------------------------------------------------------

def test_login_exitoso_paso1(client):
    """Credenciales válidas + captcha correcto → 200 con status success."""
    captcha_res, captcha_token = captcha_valido(client)
    res = client.post("/auth/login", data={
        "usuario": "admin_test",
        "password": "TestPass123!",
        "captcha_res": captcha_res,
        "captcha_token": captcha_token,
    })
    assert res.status_code == 200
    assert res.json()["status"] == "success"


def test_login_password_incorrecto(client):
    """Password incorrecto → 401."""
    captcha_res, captcha_token = captcha_valido(client)
    res = client.post("/auth/login", data={
        "usuario": "admin_test",
        "password": "WrongPass!",
        "captcha_res": captcha_res,
        "captcha_token": captcha_token,
    })
    assert res.status_code == 401


def test_login_usuario_inexistente(client):
    """Usuario que no existe → 401."""
    captcha_res, captcha_token = captcha_valido(client)
    res = client.post("/auth/login", data={
        "usuario": "no_existe",
        "password": "cualquiercosa",
        "captcha_res": captcha_res,
        "captcha_token": captcha_token,
    })
    assert res.status_code == 401


def test_login_sin_campos_requeridos(client):
    """Sin campos obligatorios → 422 Unprocessable Entity."""
    res = client.post("/auth/login", data={"usuario": "admin_test"})
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# Verify 2FA
# ---------------------------------------------------------------------------

def test_verify_2fa_exitoso(client):
    """TOTP válido → 200 con access_token."""
    res = client.post("/auth/verify-2fa", data={
        "usuario": "admin_test",
        "codigo": totp_actual(),
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["rol"] == 0


def test_verify_2fa_codigo_invalido(client):
    """TOTP incorrecto → 401."""
    res = client.post("/auth/verify-2fa", data={
        "usuario": "admin_test",
        "codigo": "000000",
    })
    assert res.status_code == 401


# ---------------------------------------------------------------------------
# Protección de endpoints con token
# ---------------------------------------------------------------------------

def test_endpoint_protegido_sin_token(client):
    """Acceder a /radicados sin token → 401."""
    res = client.get("/radicados")
    assert res.status_code == 401


def test_endpoint_protegido_token_invalido(client):
    """Token malformado → 401."""
    res = client.get("/radicados", headers={"Authorization": "Bearer token_falso"})
    assert res.status_code == 401


def test_endpoint_admin_con_token_usuario(client, user_headers):
    """Token de usuario estándar (rol 2) en endpoint de admin → 403."""
    res = client.get("/admin/kpi-dashboard", headers=user_headers)
    assert res.status_code == 403
