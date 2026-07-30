"""refresh token

Revision ID: 2da1592f0970
Revises: f8aa8f5dd94a
Create Date: 2026-07-30 15:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '2da1592f0970'
down_revision: Union[str, None] = 'f8aa8f5dd94a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('refresh_token',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('id_operador', sa.Uuid(), nullable=False),
    sa.Column('token_hash', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('criado_em', sa.DateTime(), nullable=False),
    sa.Column('expira_em', sa.DateTime(), nullable=False),
    sa.Column('revogado', sa.Boolean(), nullable=False),
    sa.Column('revogado_em', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['id_operador'], ['operador.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('token_hash')
    )
    op.create_index(op.f('ix_refresh_token_id_operador'), 'refresh_token', ['id_operador'], unique=False)
    op.create_index(op.f('ix_refresh_token_token_hash'), 'refresh_token', ['token_hash'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_refresh_token_token_hash'), table_name='refresh_token')
    op.drop_index(op.f('ix_refresh_token_id_operador'), table_name='refresh_token')
    op.drop_table('refresh_token')
