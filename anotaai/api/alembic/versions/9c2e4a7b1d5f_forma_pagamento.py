"""forma pagamento

Revision ID: 9c2e4a7b1d5f
Revises: 700e2ab1f636
Create Date: 2026-07-30 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c2e4a7b1d5f'
down_revision: Union[str, None] = '700e2ab1f636'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'comanda',
        sa.Column(
            'forma_pagamento',
            sa.Enum('DINHEIRO', 'CARTAO_CREDITO', 'CARTAO_DEBITO', 'PIX', name='formapagamento'),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column('comanda', 'forma_pagamento')
    sa.Enum(name='formapagamento').drop(op.get_bind(), checkfirst=True)
