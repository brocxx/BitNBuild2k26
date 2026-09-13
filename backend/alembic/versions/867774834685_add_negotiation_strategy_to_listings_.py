"""add_negotiation_strategy_to_listings_and_requirements

Revision ID: 867774834685
Revises: d7dea236a1ba
Create Date: 2026-09-12 23:38:46.614042
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '867774834685'
down_revision: str | None = 'd7dea236a1ba'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # SQLite requires server_default when adding NOT NULL columns to existing tables.
    with op.batch_alter_table('listings', schema=None) as batch_op:
        batch_op.add_column(sa.Column(
            'negotiation_strategy', sa.String(length=16),
            nullable=False, server_default='conceder'
        ))

    with op.batch_alter_table('requirements', schema=None) as batch_op:
        batch_op.add_column(sa.Column(
            'negotiation_strategy', sa.String(length=16),
            nullable=False, server_default='conceder'
        ))


def downgrade() -> None:
    with op.batch_alter_table('requirements', schema=None) as batch_op:
        batch_op.drop_column('negotiation_strategy')

    with op.batch_alter_table('listings', schema=None) as batch_op:
        batch_op.drop_column('negotiation_strategy')
