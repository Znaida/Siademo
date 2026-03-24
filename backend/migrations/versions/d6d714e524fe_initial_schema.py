"""initial_schema

Revision ID: d6d714e524fe
Revises: 
Create Date: 2026-03-21 12:24:25.132325

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd6d714e524fe'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'usuarios',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('usuario', sa.Text, nullable=False, unique=True),
        sa.Column('password_hash', sa.Text, nullable=False),
        sa.Column('nombre_completo', sa.Text, nullable=False),
        sa.Column('rol_id', sa.Integer, nullable=False),
        sa.Column('secret_2fa', sa.Text),
        sa.Column('activo', sa.Integer, server_default='1'),
        sa.Column('debe_cambiar_password', sa.Integer, server_default='0'),
    )
    op.create_table(
        'radicados',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('nro_radicado', sa.Text, nullable=False, unique=True),
        sa.Column('tipo_radicado', sa.Text, nullable=False),
        sa.Column('tipo_remitente', sa.Text),
        sa.Column('primer_apellido', sa.Text),
        sa.Column('segundo_apellido', sa.Text),
        sa.Column('nombre_razon_social', sa.Text),
        sa.Column('tipo_documento', sa.Text),
        sa.Column('nro_documento', sa.Text),
        sa.Column('cargo', sa.Text),
        sa.Column('direccion', sa.Text),
        sa.Column('telefono', sa.Text),
        sa.Column('correo_electronico', sa.Text),
        sa.Column('pais', sa.Text),
        sa.Column('departamento', sa.Text),
        sa.Column('ciudad', sa.Text),
        sa.Column('serie', sa.Text),
        sa.Column('subserie', sa.Text),
        sa.Column('tipo_documental', sa.Text),
        sa.Column('asunto', sa.Text),
        sa.Column('metodo_recepcion', sa.Text),
        sa.Column('nro_guia', sa.Text),
        sa.Column('nro_folios', sa.Integer),
        sa.Column('dias_respuesta', sa.Integer),
        sa.Column('fecha_vencimiento', sa.Text),
        sa.Column('fecha_radicacion', sa.Text),
        sa.Column('anexo_nombre', sa.Text),
        sa.Column('descripcion_anexo', sa.Text),
        sa.Column('seccion_responsable', sa.Text),
        sa.Column('funcionario_responsable_id', sa.Integer),
        sa.Column('con_copia', sa.Text),
        sa.Column('seccion_origen', sa.Text),
        sa.Column('funcionario_origen_id', sa.Integer),
        sa.Column('nro_radicado_relacionado', sa.Text),
        sa.Column('activa_flujo_id', sa.Integer),
        sa.Column('path_principal', sa.Text),
        sa.Column('anexos_json', sa.Text),
        sa.Column('creado_por', sa.Integer),
        sa.Column('estado', sa.Text, server_default='Radicado'),
    )
    op.create_table(
        'auditoria',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('usuario_id', sa.Integer),
        sa.Column('accion', sa.Text),
        sa.Column('modulo', sa.Text),
        sa.Column('detalle', sa.Text),
        sa.Column('ip_origen', sa.Text),
        sa.Column('fecha_accion', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_table(
        'equipos',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('nombre', sa.Text, nullable=False, unique=True),
    )
    op.create_table(
        'usuario_equipo',
        sa.Column('usuario_id', sa.Integer, nullable=False),
        sa.Column('equipo_id', sa.Integer, nullable=False),
        sa.PrimaryKeyConstraint('usuario_id', 'equipo_id'),
    )
    op.create_table(
        'estructura_organica',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('entidad', sa.Text),
        sa.Column('unidad', sa.Text),
        sa.Column('oficina', sa.Text),
        sa.Column('depende_de', sa.Text),
    )
    op.create_table(
        'trd',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('cod_unidad', sa.Text),
        sa.Column('unidad', sa.Text),
        sa.Column('cod_oficina', sa.Text),
        sa.Column('oficina', sa.Text),
        sa.Column('cod_serie', sa.Text),
        sa.Column('nombre_serie', sa.Text),
        sa.Column('cod_subserie', sa.Text),
        sa.Column('nombre_subserie', sa.Text),
        sa.Column('tipo_documental', sa.Text),
        sa.Column('soporte', sa.Text),
        sa.Column('extension', sa.Text),
        sa.Column('años_gestion', sa.Integer),
        sa.Column('años_central', sa.Integer),
        sa.Column('disposicion_final', sa.Text),
        sa.Column('porcentaje_seleccion', sa.Integer),
        sa.Column('procedimiento', sa.Text),
        sa.Column('llaves_busqueda', sa.Text),
    )
    op.create_table(
        'secuencia_radicados',
        sa.Column('prefijo', sa.Text, nullable=False),
        sa.Column('anio', sa.Integer, nullable=False),
        sa.Column('ultimo_numero', sa.Integer, server_default='0'),
        sa.PrimaryKeyConstraint('prefijo', 'anio'),
    )
    op.create_table(
        'trazabilidad_radicados',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('nro_radicado', sa.Text, nullable=False),
        sa.Column('accion', sa.Text, nullable=False),
        sa.Column('comentario', sa.Text),
        sa.Column('desde_usuario_id', sa.Integer),
        sa.Column('hacia_usuario_id', sa.Integer),
        sa.Column('estado_nuevo', sa.Text),
        sa.Column('fecha', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_table(
        'notificaciones',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('usuario_id', sa.Integer, nullable=False),
        sa.Column('nro_radicado', sa.Text, nullable=False),
        sa.Column('mensaje', sa.Text, nullable=False),
        sa.Column('leida', sa.Integer, server_default='0'),
        sa.Column('fecha', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_table(
        'archivo_central',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('nro_radicado', sa.Text, nullable=False, unique=True),
        sa.Column('serie', sa.Text),
        sa.Column('subserie', sa.Text),
        sa.Column('tipo_documental', sa.Text),
        sa.Column('asunto', sa.Text),
        sa.Column('anio_produccion', sa.Integer),
        sa.Column('caja', sa.Text),
        sa.Column('carpeta', sa.Text),
        sa.Column('folio_inicio', sa.Integer),
        sa.Column('folio_fin', sa.Integer),
        sa.Column('llaves_busqueda', sa.Text),
        sa.Column('observaciones', sa.Text),
        sa.Column('disposicion_final', sa.Text),
        sa.Column('path_principal', sa.Text),
        sa.Column('fecha_transferencia', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('transferido_por', sa.Integer),
    )


def downgrade() -> None:
    op.drop_table('archivo_central')
    op.drop_table('notificaciones')
    op.drop_table('trazabilidad_radicados')
    op.drop_table('secuencia_radicados')
    op.drop_table('trd')
    op.drop_table('estructura_organica')
    op.drop_table('usuario_equipo')
    op.drop_table('equipos')
    op.drop_table('auditoria')
    op.drop_table('radicados')
    op.drop_table('usuarios')
