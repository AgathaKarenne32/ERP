"""venda processada

Revision ID: 430b9a9ffe0b
Revises: 7fb96b2c364a
Create Date: 2026-07-30 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '430b9a9ffe0b'
down_revision: Union[str, None] = '7fb96b2c364a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'venda_processada',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('id_loja', sa.Uuid(), nullable=False),
        sa.Column('referencia', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('criado_em', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['id_loja'], ['loja.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('id_loja', 'referencia', name='uq_venda_processada_loja_referencia'),
    )
    op.create_index(op.f('ix_venda_processada_id_loja'), 'venda_processada', ['id_loja'], unique=False)
    op.create_index(op.f('ix_venda_processada_referencia'), 'venda_processada', ['referencia'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_venda_processada_referencia'), table_name='venda_processada')
    op.drop_index(op.f('ix_venda_processada_id_loja'), table_name='venda_processada')
    op.drop_table('venda_processada')
