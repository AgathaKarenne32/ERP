"""integracao loja

Revision ID: 700e2ab1f636
Revises: 2da1592f0970
Create Date: 2026-07-30 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '700e2ab1f636'
down_revision: Union[str, None] = '2da1592f0970'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 'origempedido' já existe como tipo ENUM no Postgres (criado na
    # migração de schema inicial) — create_type=False evita tentar
    # recriar o mesmo tipo e quebrar com "type already exists".
    provedor_enum = postgresql.ENUM('SALAO', 'IFOOD', 'WHATSAPP', name='origempedido', create_type=False)

    op.create_table(
        'integracao_loja',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('id_loja', sa.Uuid(), nullable=False),
        sa.Column('provedor', provedor_enum, nullable=False),
        sa.Column('identificador_externo', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('criado_em', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provedor', 'identificador_externo', name='uq_integracao_provedor_identificador'),
    )
    op.create_index(op.f('ix_integracao_loja_id_loja'), 'integracao_loja', ['id_loja'], unique=False)
    op.create_index(
        op.f('ix_integracao_loja_identificador_externo'), 'integracao_loja', ['identificador_externo'], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_integracao_loja_identificador_externo'), table_name='integracao_loja')
    op.drop_index(op.f('ix_integracao_loja_id_loja'), table_name='integracao_loja')
    op.drop_table('integracao_loja')
