"""Add new syncer table

Revision ID: 2a07b543335e
Revises: a2e2aab8f331
Create Date: 2020-12-27 09:35:44.017981

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2a07b543335e'
down_revision = 'a2e2aab8f331'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
            'blockchain_sync',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('blockchain', sa.String, nullable=False),
            sa.Column('block_start', sa.Integer, nullable=False, default=0),
            sa.Column('tx_start', sa.Integer, nullable=False, default=0),
            sa.Column('block_cursor', sa.Integer, nullable=False, default=0),
            sa.Column('tx_cursor', sa.Integer, nullable=False, default=0),
            sa.Column('block_target', sa.Integer, nullable=True),
            sa.Column('date_created', sa.DateTime, nullable=False),
            sa.Column('date_updated', sa.DateTime),
            )


def downgrade():
    op.drop_table('blockchain_sync')
