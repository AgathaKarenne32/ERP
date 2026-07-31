"""desconto total

Revision ID: b3d4e5f6a7c8
Revises: 9c2e4a7b1d5f
Create Date: 2026-07-31 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3d4e5f6a7c8'
down_revision: Union[str, None] = '9c2e4a7b1d5f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'comanda',
        sa.Column('desconto_total', sa.Float(), nullable=False, server_default='0'),
    )


def downgrade() -> None:
    op.drop_column('comanda', 'desconto_total')
