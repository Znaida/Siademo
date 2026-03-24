"""add_fecha_radicacion_hash_sha256

Revision ID: ea617457f2d7
Revises: d6d714e524fe
Create Date: 2026-03-21 12:36:30.483739

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ea617457f2d7'
down_revision: Union[str, Sequence[str], None] = 'd6d714e524fe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('radicados') as batch_op:
        batch_op.add_column(sa.Column('fecha_radicacion', sa.Text))
        batch_op.add_column(sa.Column('hash_sha256', sa.Text))


def downgrade() -> None:
    with op.batch_alter_table('radicados') as batch_op:
        batch_op.drop_column('hash_sha256')
        batch_op.drop_column('fecha_radicacion')
