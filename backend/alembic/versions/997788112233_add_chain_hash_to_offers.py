"""add_chain_hash_to_offers

Revision ID: 997788112233
Revises: 867774834685
Create Date: 2026-09-13 00:36:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '997788112233'
down_revision: str | None = '867774834685'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    cols = [c['name'] for c in insp.get_columns('offers')]
    if 'chain_hash' not in cols:
        with op.batch_alter_table('offers', schema=None) as batch_op:
            batch_op.add_column(sa.Column(
                'chain_hash', sa.String(length=64),
                nullable=False, server_default=''
            ))


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    cols = [c['name'] for c in insp.get_columns('offers')]
    if 'chain_hash' in cols:
        with op.batch_alter_table('offers', schema=None) as batch_op:
            batch_op.drop_column('chain_hash')

