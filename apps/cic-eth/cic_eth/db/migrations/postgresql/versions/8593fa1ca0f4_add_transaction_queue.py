"""Add transaction queue

Revision ID: 8593fa1ca0f4
Revises: 
Create Date: 2020-09-22 21:56:42.117047

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8593fa1ca0f4'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
            'otx',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('date_created', sa.DateTime, nullable=False),
            sa.Column('nonce', sa.Integer, nullable=False),
            sa.Column('tx_hash', sa.String(66), nullable=False),
            sa.Column('signed_tx', sa.Text, nullable=False),
            sa.Column('status', sa.Integer, nullable=False, default=-9),
            sa.Column('block', sa.Integer),
            )
    op.create_index('idx_otx_tx', 'otx', ['tx_hash'], unique=True)


def downgrade():
    op.drop_index('idx_otx_tx')
    op.drop_table('otx')
