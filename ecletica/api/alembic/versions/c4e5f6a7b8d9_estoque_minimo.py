"""estoque minimo

Revision ID: c4e5f6a7b8d9
Revises: a1c3f9d02b77
Create Date: 2026-07-31 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4e5f6a7b8d9'
down_revision: Union[str, None] = 'a1c3f9d02b77'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'insumo',
        sa.Column('estoque_minimo', sa.Float(), nullable=False, server_default='0'),
    )


def downgrade() -> None:
    op.drop_column('insumo', 'estoque_minimo')
