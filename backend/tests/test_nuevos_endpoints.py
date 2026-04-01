"""
Tests para los nuevos endpoints implementados en F7/F8:
- Recuperación de contraseña (solicitar-reset, reset-password)
- Workflows BPMN (GET/POST/PUT/DELETE /admin/workflows)
- Validación de archivos en radicación
- Logout (JWT blacklist)
- Historial con control de acceso
"""
import io
import sqlite3
import os
import pytest
from fastapi.testclient import TestClient

_TEST_DB = os.environ.get("TEST_DB_PATH", "")


# ── Helpers ────────────────────────────────────────────────────────────────────

def get_conn():
    conn = sqlite3.connect(_TEST_DB)
    conn.row_factory = sqlite3.Row
    return conn


SAMPLE_BPMN = """<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  id="Definitions_test" targetNamespace="http://test.siade">
  <bpmn:process id="TestProcess" isExecutable="true">
    <bpmn:startEvent id="inicio"><bpmn:outgoing>f1</bpmn:outgoing></bpmn:startEvent>
    <bpmn:endEvent id="fin"><bpmn:incoming>f1</bpmn:incoming></bpmn:endEvent>
    <bpmn:sequenceFlow id="f1" sourceRef="inicio" targetRef="fin"/>
  </bpmn:process>
</bpmn:definitions>"""


# ══════════════════════════════════════════════════════════════════════════════
# TESTS: Recuperación de contraseña
# ══════════════════════════════════════════════════════════════════════════════

class TestSolicitarReset:
    """POST /auth/solicitar-reset — requiere autenticación de admin"""

    def test_solicitar_reset_sin_auth_rechazado(self, client):
        res = client.post("/auth/solicitar-reset", data={"usuario": "user_test"})
        assert res.status_code == 401

    def test_solicitar_reset_con_usuario_auth_rechazado(self, client, user_headers):
        # user_override sólo override obtener_usuario_actual, no obtener_admin_actual.
        # Usamos JWT real con rol=2 para que obtener_admin_actual devuelva 403.
        res = client.post("/auth/solicitar-reset", data={"usuario": "user_test"}, headers=user_headers)
        assert res.status_code == 403

    def test_solicitar_reset_usuario_inexistente_respuesta_generica(self, admin_override):
        res = admin_override.post("/auth/solicitar-reset", data={"usuario": "no_existe_xyz"})
        assert res.status_code == 200
        data = res.json()
        assert "mensaje" in data
        assert "token" not in data  # token NO debe exponerse en respuesta

    def test_solicitar_reset_usuario_existente_no_expone_token(self, admin_override):
        res = admin_override.post("/auth/solicitar-reset", data={"usuario": "user_test"})
        assert res.status_code == 200
        data = res.json()
        assert "mensaje" in data
        assert "token" not in data  # seguridad C-03: token no en respuesta

    def test_solicitar_reset_crea_token_en_bd(self, admin_override):
        admin_override.post("/auth/solicitar-reset", data={"usuario": "user_test"})
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as total FROM password_reset_tokens WHERE usuario_id = 2")
        total = cur.fetchone()["total"]
        conn.close()
        assert total >= 1


class TestResetPassword:
    """POST /auth/reset-password — no requiere auth, usa token temporal"""

    def _generar_token(self, admin_override) -> str:
        """Helper: genera token via admin y lo extrae de la BD"""
        admin_override.post("/auth/solicitar-reset", data={"usuario": "user_test"})
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT token FROM password_reset_tokens
            WHERE usuario_id = 2 AND usado = 0
            ORDER BY id DESC LIMIT 1
        """)
        row = cur.fetchone()
        conn.close()
        return row["token"] if row else ""

    def test_reset_token_invalido(self, client):
        res = client.post("/auth/reset-password", data={
            "token": "token_falso_xyz",
            "password_nuevo": "NuevaPass123!",
            "password_confirmar": "NuevaPass123!"
        })
        assert res.status_code == 400

    def test_reset_passwords_no_coinciden(self, admin_override):
        token = self._generar_token(admin_override)
        res = admin_override.post("/auth/reset-password", data={
            "token": token,
            "password_nuevo": "NuevaPass123!",
            "password_confirmar": "OtraPass456!"
        })
        assert res.status_code == 400
        assert "coinciden" in res.json()["detail"].lower()

    def test_reset_password_muy_corta(self, admin_override):
        token = self._generar_token(admin_override)
        res = admin_override.post("/auth/reset-password", data={
            "token": token,
            "password_nuevo": "abc",
            "password_confirmar": "abc"
        })
        assert res.status_code == 400

    def test_reset_password_exitoso(self, admin_override):
        token = self._generar_token(admin_override)
        assert token, "No se pudo obtener token de reset"
        res = admin_override.post("/auth/reset-password", data={
            "token": token,
            "password_nuevo": "TestPass123!",
            "password_confirmar": "TestPass123!"
        })
        assert res.status_code == 200
        assert "exitosamente" in res.json()["mensaje"].lower()

    def test_reset_token_usado_no_reutilizable(self, admin_override):
        token = self._generar_token(admin_override)
        admin_override.post("/auth/reset-password", data={
            "token": token,
            "password_nuevo": "TestPass123!",
            "password_confirmar": "TestPass123!"
        })
        # Intentar usar el mismo token de nuevo
        res = admin_override.post("/auth/reset-password", data={
            "token": token,
            "password_nuevo": "OtraPass456!",
            "password_confirmar": "OtraPass456!"
        })
        assert res.status_code == 400


# ══════════════════════════════════════════════════════════════════════════════
# TESTS: Workflows BPMN
# ══════════════════════════════════════════════════════════════════════════════

class TestWorkflows:
    """CRUD /admin/workflows"""

    def test_listar_workflows_sin_auth(self, client):
        res = client.get("/admin/workflows")
        assert res.status_code == 401

    def test_listar_workflows_como_admin(self, admin_override):
        res = admin_override.get("/admin/workflows")
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)

    def test_listar_workflows_contiene_plantillas_default(self, admin_override):
        res = admin_override.get("/admin/workflows")
        assert res.status_code == 200
        data = res.json()
        # Las 4 plantillas prediseñadas deben existir (seed T8.5)
        tipos = [w["tipo"] for w in data]
        assert "entrada" in tipos
        assert "salida" in tipos
        assert "interna" in tipos
        assert "archivo" in tipos

    def test_crear_workflow_sin_auth(self, client):
        res = client.post("/admin/workflows", json={
            "nombre": "Test", "tipo": "entrada", "xml_content": SAMPLE_BPMN
        })
        assert res.status_code == 401

    def test_crear_workflow_tipo_invalido(self, admin_override):
        res = admin_override.post("/admin/workflows", json={
            "nombre": "Test inválido",
            "tipo": "tipo_inexistente",
            "xml_content": SAMPLE_BPMN
        })
        assert res.status_code == 400

    def test_crear_workflow_sin_nombre(self, admin_override):
        res = admin_override.post("/admin/workflows", json={
            "nombre": "",
            "tipo": "entrada",
            "xml_content": SAMPLE_BPMN
        })
        assert res.status_code == 400

    def test_crear_workflow_exitoso(self, admin_override):
        res = admin_override.post("/admin/workflows", json={
            "nombre": "Flujo personalizado test",
            "tipo": "entrada",
            "descripcion": "Test de creación",
            "xml_content": SAMPLE_BPMN
        })
        assert res.status_code == 200
        data = res.json()
        assert "id" in data
        assert data["id"] > 0

    def test_obtener_workflow_por_id(self, admin_override):
        # Crear primero
        create_res = admin_override.post("/admin/workflows", json={
            "nombre": "Flujo para obtener",
            "tipo": "salida",
            "xml_content": SAMPLE_BPMN
        })
        wf_id = create_res.json()["id"]

        # Obtener por ID
        res = admin_override.get(f"/admin/workflows/{wf_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == wf_id
        assert data["nombre"] == "Flujo para obtener"
        assert "xml_content" in data

    def test_obtener_workflow_inexistente(self, admin_override):
        res = admin_override.get("/admin/workflows/99999")
        assert res.status_code == 404

    def test_actualizar_workflow(self, admin_override):
        create_res = admin_override.post("/admin/workflows", json={
            "nombre": "Flujo para actualizar",
            "tipo": "interna",
            "xml_content": SAMPLE_BPMN
        })
        wf_id = create_res.json()["id"]

        res = admin_override.put(f"/admin/workflows/{wf_id}", json={
            "nombre": "Flujo actualizado",
            "xml_content": SAMPLE_BPMN
        })
        assert res.status_code == 200
        data = res.json()
        assert "version" in data
        assert data["version"] == 2

    def test_eliminar_workflow_creado(self, admin_override):
        create_res = admin_override.post("/admin/workflows", json={
            "nombre": "Flujo para eliminar",
            "tipo": "archivo",
            "xml_content": SAMPLE_BPMN
        })
        wf_id = create_res.json()["id"]

        res = admin_override.delete(f"/admin/workflows/{wf_id}")
        assert res.status_code == 200

        # Verificar que ya no existe
        get_res = admin_override.get(f"/admin/workflows/{wf_id}")
        assert get_res.status_code == 404

    def test_no_eliminar_plantilla_default(self, admin_override):
        # Obtener el ID de una plantilla default
        res = admin_override.get("/admin/workflows")
        default = next((w for w in res.json() if w.get("es_default")), None)
        assert default is not None, "Debe existir al menos una plantilla default"

        del_res = admin_override.delete(f"/admin/workflows/{default['id']}")
        assert del_res.status_code == 403


# ══════════════════════════════════════════════════════════════════════════════
# TESTS: Validación de archivos en radicación
# ══════════════════════════════════════════════════════════════════════════════

class TestValidacionArchivos:
    """Validación de extensión y tamaño en POST /radicar"""

    _METADATA_BASE = {
        "tipo_radicado": "RECIBIDA",
        "nombre_razon_social": "Test Ciudadano",
        "asunto": "Test de validación de archivos",
        "serie": "Contratos",
        "subserie": "General",
        "tipo_documental": "Solicitud",
        "dias_respuesta": 15,
        "tipo_remitente": "CIUDADANO",
        "tipo_documento": "CC",
        "nro_documento": "12345678",
        "departamento": "Caldas",
        "ciudad": "Manizales",
        "metodo_recepcion": "PRESENCIAL",
        "seccion_responsable": "Ventanilla",
        "funcionario_responsable_id": 1,
    }

    def test_extension_no_permitida_rechazada(self, user_override):
        import json
        metadata = json.dumps({**self._METADATA_BASE, "asunto": "Test extensión no permitida"})
        archivo_exe = io.BytesIO(b"MZ\x90\x00fake_executable")
        res = user_override.post("/radicar", data={"metadata": metadata}, files={
            "archivo_principal": ("malware.exe", archivo_exe, "application/octet-stream")
        })
        assert res.status_code == 400
        assert "no permitido" in res.json()["detail"].lower()

    def test_extension_permitida_aceptada(self, user_override, tmp_path):
        import json
        metadata = json.dumps({**self._METADATA_BASE, "asunto": "Solicitud de prueba extensión válida"})
        pdf_content = b"%PDF-1.4 fake pdf content for testing"
        res = user_override.post("/radicar", data={"metadata": metadata}, files={
            "archivo_principal": ("documento.pdf", io.BytesIO(pdf_content), "application/pdf")
        })
        # Puede fallar por otras razones (UPLOAD_DIR no existe) pero NO por extensión
        assert res.status_code != 400 or "no permitido" not in res.json().get("detail", "")

    def test_archivo_demasiado_grande_rechazado(self, user_override):
        import json
        metadata = json.dumps({**self._METADATA_BASE, "asunto": "Test tamaño excedido"})
        # Simular archivo mayor a 20MB
        archivo_grande = io.BytesIO(b"x" * (21 * 1024 * 1024))
        res = user_override.post("/radicar", data={"metadata": metadata}, files={
            "archivo_principal": ("grande.pdf", archivo_grande, "application/pdf")
        })
        assert res.status_code == 413


# ══════════════════════════════════════════════════════════════════════════════
# TESTS: Historial con control de acceso (M-07)
# ══════════════════════════════════════════════════════════════════════════════

class TestHistorialAcceso:
    """Control de acceso IDOR en historial de radicado"""

    def test_admin_ve_cualquier_historial(self, admin_override):
        res = admin_override.get("/radicados/RAD-2026-00001/historial")
        assert res.status_code == 200

    def test_usuario_ve_historial_de_su_radicado(self, user_override):
        # user_test (id=2) es responsable de ENV-2026-00001
        res = user_override.get("/radicados/ENV-2026-00001/historial")
        assert res.status_code == 200

    def test_usuario_no_ve_historial_ajeno(self, user_override):
        # ADM-2026-00099: creado_por=1, funcionario_responsable_id=1 — user_test (id=2) no tiene acceso.
        # Usamos este radicado dedicado para evitar interferencia de test_crud.py (que traslada RAD-2026-00001 a user_id=2).
        res = user_override.get("/radicados/ADM-2026-00099/historial")
        assert res.status_code == 403

    def test_historial_radicado_inexistente(self, user_override):
        res = user_override.get("/radicados/RAD-9999-99999/historial")
        assert res.status_code == 403  # sin acceso = 403, no revela existencia


# ══════════════════════════════════════════════════════════════════════════════
# TESTS: Logout
# ══════════════════════════════════════════════════════════════════════════════

class TestLogout:
    """POST /auth/logout — requiere token válido"""

    def test_logout_sin_token_rechazado(self, client):
        res = client.post("/auth/logout")
        assert res.status_code == 401

    def test_logout_con_token_valido(self, user_override):
        res = user_override.post("/auth/logout")
        assert res.status_code == 200
        assert "cerrada" in res.json()["mensaje"].lower()
