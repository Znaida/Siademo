"""
Tests unitarios directos de funciones CRUD (sin HTTP).
Prueban la lógica de negocio aislada del framework.
"""
import pytest
from fastapi import HTTPException
from app.crud.radicado import (
    listar_radicados, get_path_documento,
    historial_radicado, trasladar_radicado, archivar_radicado
)
from app.crud.usuario import (
    crear_usuario, listar_usuarios, cambiar_estado_usuario, get_usuario_por_id
)
from app.crud.auditoria import consultar_logs, exportar_logs_csv
from app.schemas.radicado import TrasladoData, ArchivarData


# ---------------------------------------------------------------------------
# listar_radicados
# ---------------------------------------------------------------------------

def test_listar_radicados_admin_ve_todo(setup_test_db):
    """Rol 0 (admin) ve todos los radicados."""
    resultado = listar_radicados(user_id=1, rol=0)
    assert resultado["total"] >= 3
    assert len(resultado["items"]) >= 3


def test_listar_radicados_usuario_filtrado(setup_test_db):
    """Rol > 1 solo ve radicados donde es creador o responsable."""
    resultado = listar_radicados(user_id=2, rol=2)
    for item in resultado["items"]:
        assert item["creado_por"] == 2 or item["funcionario_responsable_id"] == 2


def test_listar_radicados_paginacion(setup_test_db):
    """Paginación: page=1, per_page=1 devuelve exactamente 1 item."""
    resultado = listar_radicados(user_id=1, rol=0, page=1, per_page=1)
    assert len(resultado["items"]) == 1
    assert resultado["per_page"] == 1
    assert resultado["total_pages"] >= 3


def test_listar_radicados_filtro_tipo(setup_test_db):
    """Filtro tipo_doc limita los resultados correctamente."""
    resultado = listar_radicados(user_id=1, rol=0, tipo_doc="RECIBIDA")
    assert resultado["total"] >= 1
    for item in resultado["items"]:
        assert item["tipo_radicado"] == "RECIBIDA"


def test_listar_radicados_filtro_estado(setup_test_db):
    """Filtro estado limita los resultados al estado indicado."""
    resultado = listar_radicados(user_id=1, rol=0, estado="Archivado")
    for item in resultado["items"]:
        assert item["estado"] == "Archivado"


def test_listar_radicados_busqueda_libre(setup_test_db):
    """Búsqueda libre q encuentra resultados por asunto."""
    resultado = listar_radicados(user_id=1, rol=0, q="Solicitud")
    assert resultado["total"] >= 1


def test_listar_radicados_busqueda_inexistente(setup_test_db):
    """Búsqueda sin coincidencias retorna 0 resultados."""
    resultado = listar_radicados(user_id=1, rol=0, q="zzzxxx_sin_resultados")
    assert resultado["total"] == 0


def test_listar_radicados_filtro_serie(setup_test_db):
    """Filtro serie_filtro retorna solo radicados con esa serie."""
    resultado = listar_radicados(user_id=1, rol=0, serie_filtro="Contratos")
    assert resultado["total"] >= 1
    for item in resultado["items"]:
        assert "Contratos" in (item["serie"] or "")


def test_listar_radicados_estructura_respuesta(setup_test_db):
    """La respuesta tiene todas las claves de paginación."""
    resultado = listar_radicados(user_id=1, rol=0)
    for key in ["items", "total", "page", "per_page", "total_pages"]:
        assert key in resultado


# ---------------------------------------------------------------------------
# get_path_documento
# ---------------------------------------------------------------------------

def test_get_path_documento_admin(setup_test_db):
    """Admin puede acceder al path de cualquier documento."""
    path = get_path_documento("RAD-2026-00001", user_id=1, rol=0)
    assert path == "/tmp/doc1.pdf"


def test_get_path_documento_propietario(setup_test_db):
    """Usuario propietario puede acceder a su propio documento."""
    # RAD-2026-00002 tiene funcionario_responsable_id=2
    path = get_path_documento("RAD-2026-00002", user_id=2, rol=2)
    assert path == "/tmp/doc2.pdf"


def test_get_path_documento_sin_acceso(setup_test_db):
    """Usuario sin acceso al radicado recibe None."""
    # RAD-2026-00001 tiene creado_por=1, funcionario_responsable_id=1 — user_id=2 no tiene acceso
    path = get_path_documento("RAD-2026-00001", user_id=2, rol=2)
    assert path is None


def test_get_path_documento_inexistente(setup_test_db):
    """Radicado que no existe → None."""
    path = get_path_documento("RAD-9999-99999", user_id=1, rol=0)
    assert path is None


# ---------------------------------------------------------------------------
# historial_radicado
# ---------------------------------------------------------------------------

def test_historial_radicado_retorna_lista(setup_test_db):
    """historial_radicado siempre retorna una lista."""
    resultado = historial_radicado("RAD-2026-00001")
    assert isinstance(resultado, list)


def test_historial_radicado_con_entradas(setup_test_db):
    """Radicado con historial retorna entradas con los campos correctos."""
    resultado = historial_radicado("RAD-2026-00001")
    assert len(resultado) >= 1
    primera = resultado[0]
    assert "accion" in primera
    assert "estado_nuevo" in primera
    assert primera["accion"] == "CREACION"


def test_historial_radicado_tiene_multiples_entradas(setup_test_db):
    """Radicado con múltiples eventos tiene al menos 2 entradas en historial."""
    resultado = historial_radicado("RAD-2026-00002")
    assert len(resultado) >= 2
    acciones = [e["accion"] for e in resultado]
    assert "CREACION" in acciones
    assert "ARCHIVADO" in acciones


def test_historial_radicado_inexistente_retorna_vacio(setup_test_db):
    """Radicado que no existe → lista vacía (no excepción)."""
    resultado = historial_radicado("RAD-0000-00000")
    assert resultado == []


# ---------------------------------------------------------------------------
# trasladar_radicado
# ---------------------------------------------------------------------------

def test_trasladar_radicado_como_admin(setup_test_db):
    """Admin puede trasladar a otro usuario activo."""
    data = TrasladoData(nuevo_responsable_id=2, comentario="Traslado CRUD test")
    resultado = trasladar_radicado("RAD-2026-00001", data, user_id=1, rol=0)
    assert "mensaje" in resultado
    assert "User Test" in resultado["mensaje"]


def test_trasladar_radicado_inexistente(setup_test_db):
    """Trasladar radicado que no existe → HTTPException 404."""
    data = TrasladoData(nuevo_responsable_id=1, comentario="test")
    with pytest.raises(HTTPException) as exc:
        trasladar_radicado("RAD-0000-00000", data, user_id=1, rol=0)
    assert exc.value.status_code == 404


def test_trasladar_a_usuario_inactivo_o_inexistente(setup_test_db):
    """Trasladar a usuario que no existe → HTTPException 404."""
    data = TrasladoData(nuevo_responsable_id=9999, comentario="test")
    with pytest.raises(HTTPException) as exc:
        trasladar_radicado("RAD-2026-00002", data, user_id=1, rol=0)
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# archivar_radicado
# ---------------------------------------------------------------------------

def test_archivar_radicado_como_admin(setup_test_db):
    """Admin puede archivar cualquier radicado."""
    data = ArchivarData(comentario="Archivado en test CRUD")
    resultado = archivar_radicado("ENV-2026-00001", data, user_id=1, rol=0)
    assert "mensaje" in resultado
    assert "archivado" in resultado["mensaje"].lower()


def test_archivar_radicado_inexistente(setup_test_db):
    """Archivar radicado que no existe → HTTPException 404."""
    data = ArchivarData(comentario="test")
    with pytest.raises(HTTPException) as exc:
        archivar_radicado("RAD-0000-00000", data, user_id=1, rol=0)
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# crud/usuario
# ---------------------------------------------------------------------------

def test_crear_usuario_nuevo(setup_test_db):
    """crear_usuario inserta un usuario nuevo sin error."""
    crear_usuario("crud_test_user", "CRUD Test User", 2, "hashed_pw", "JBSWY3DPEHPK3PXP")
    resultado = listar_usuarios()
    usuarios = [u["usuario"] for u in resultado]
    assert "crud_test_user" in usuarios


def test_crear_usuario_duplicado_lanza_error(setup_test_db):
    """crear_usuario con usuario duplicado → HTTPException 400."""
    with pytest.raises(HTTPException) as exc:
        crear_usuario("user_test", "Dup", 2, "hashed_pw", "JBSWY3DPEHPK3PXP")
    assert exc.value.status_code == 400


def test_listar_usuarios_excluye_admin(setup_test_db):
    """listar_usuarios no incluye usuarios con rol_id=0."""
    resultado = listar_usuarios()
    roles = [u["rol_id"] for u in resultado]
    assert 0 not in roles


def test_listar_usuarios_incluye_funcionarios(setup_test_db):
    """listar_usuarios incluye usuarios con rol > 0."""
    resultado = listar_usuarios()
    usuarios = [u["usuario"] for u in resultado]
    assert "user_test" in usuarios


def test_cambiar_estado_usuario_desactivar(setup_test_db):
    """cambiar_estado_usuario desactiva un usuario."""
    cambiar_estado_usuario(2, False)
    usuario = get_usuario_por_id(2)
    assert usuario["activo"] == 0


def test_cambiar_estado_usuario_activar(setup_test_db):
    """cambiar_estado_usuario reactiva un usuario."""
    cambiar_estado_usuario(2, True)
    usuario = get_usuario_por_id(2)
    assert usuario["activo"] == 1


def test_cambiar_estado_usuario_inexistente(setup_test_db):
    """cambiar_estado_usuario con ID inexistente → HTTPException 404."""
    with pytest.raises(HTTPException) as exc:
        cambiar_estado_usuario(9999, False)
    assert exc.value.status_code == 404


def test_get_usuario_por_id_existente(setup_test_db):
    """get_usuario_por_id retorna dict con campos correctos."""
    usuario = get_usuario_por_id(1)
    assert usuario is not None
    assert usuario["usuario"] == "admin_test"
    assert "nombre_completo" in usuario


def test_get_usuario_por_id_inexistente(setup_test_db):
    """get_usuario_por_id con ID inexistente retorna None."""
    resultado = get_usuario_por_id(9999)
    assert resultado is None


# ---------------------------------------------------------------------------
# crud/auditoria
# ---------------------------------------------------------------------------

def test_consultar_logs_retorna_estructura(setup_test_db):
    """consultar_logs retorna estructura paginada correcta."""
    resultado = consultar_logs()
    assert "items" in resultado
    assert "total" in resultado
    assert "page" in resultado
    assert "per_page" in resultado
    assert "total_pages" in resultado


def test_consultar_logs_filtro_modulo(setup_test_db):
    """Filtro modulo=AUTH limita resultados."""
    resultado = consultar_logs(modulo="AUTH")
    for item in resultado["items"]:
        assert item["modulo"] == "AUTH"


def test_consultar_logs_filtro_accion(setup_test_db):
    """Filtro accion busca por texto parcial — retorna solo ítems que coinciden."""
    resultado = consultar_logs(accion="LOGIN")
    # SQLite LIKE es case-insensitive, el campo puede ser "LOGIN_SUCCESS" o "POST /auth/login"
    for item in resultado["items"]:
        assert "login" in item["accion"].lower()


def test_consultar_logs_filtro_usuario(setup_test_db):
    """Filtro usuario busca por nombre parcial."""
    resultado = consultar_logs(usuario="admin")
    assert isinstance(resultado["items"], list)


def test_consultar_logs_filtro_fechas(setup_test_db):
    """Filtro fecha_desde y fecha_hasta funciona sin error."""
    resultado = consultar_logs(fecha_desde="2026-01-01", fecha_hasta="2026-12-31")
    assert isinstance(resultado["items"], list)


def test_consultar_logs_paginacion(setup_test_db):
    """Paginación con per_page=2 retorna máximo 2 items."""
    resultado = consultar_logs(page=1, per_page=2)
    assert resultado["per_page"] == 2
    assert len(resultado["items"]) <= 2


def test_exportar_logs_csv_retorna_string(setup_test_db):
    """exportar_logs_csv retorna string CSV con cabecera."""
    csv_content = exportar_logs_csv()
    assert isinstance(csv_content, str)
    assert "ID" in csv_content
    assert "Fecha" in csv_content
    assert "Usuario" in csv_content


def test_exportar_logs_csv_con_filtros(setup_test_db):
    """exportar_logs_csv con filtros no genera error."""
    csv_content = exportar_logs_csv(modulo="AUTH", fecha_desde="2026-01-01")
    assert isinstance(csv_content, str)


def test_exportar_logs_csv_filtro_accion(setup_test_db):
    """exportar_logs_csv con filtro accion retorna CSV."""
    csv_content = exportar_logs_csv(accion="LOGIN", usuario="admin")
    assert isinstance(csv_content, str)
    assert "ID" in csv_content
