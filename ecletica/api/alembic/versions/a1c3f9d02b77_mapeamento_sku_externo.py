"""mapeamento sku externo

Revision ID: a1c3f9d02b77
Revises: 430b9a9ffe0b
Create Date: 2026-07-30 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'a1c3f9d02b77'
down_revision: Union[str, None] = '430b9a9ffe0b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'mapeamento_sku_externo',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('id_produto', sa.Uuid(), nullable=False),
        sa.Column('provedor', sa.Enum('IFOOD', 'WHATSAPP', name='provedorexterno'), nullable=False),
        sa.Column('sku_externo', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('criado_em', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['id_produto'], ['produto.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provedor', 'sku_externo', name='uq_mapeamento_sku_provedor_sku'),
    )
    op.create_index(op.f('ix_mapeamento_sku_externo_id_produto'), 'mapeamento_sku_externo', ['id_produto'], unique=False)
    op.create_index(op.f('ix_mapeamento_sku_externo_sku_externo'), 'mapeamento_sku_externo', ['sku_externo'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_mapeamento_sku_externo_sku_externo'), table_name='mapeamento_sku_externo')
    op.drop_index(op.f('ix_mapeamento_sku_externo_id_produto'), table_name='mapeamento_sku_externo')
    op.drop_table('mapeamento_sku_externo')
    sa.Enum(name='provedorexterno').drop(op.get_bind(), checkfirst=True)
