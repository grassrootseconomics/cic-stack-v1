"""Add otx state log

Revision ID: 6ac7a1dadc46
Revises: 89e1e9baa53c
Create Date: 2021-01-30 13:59:49.022373

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6ac7a1dadc46'
down_revision = '89e1e9baa53c'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
            'otx_state_log',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('otx_id', sa.Integer, sa.ForeignKey('otx.id'), nullable=False),
            sa.Column('date', sa.DateTime, nullable=False),
            sa.Column('status', sa.Integer, nullable=False),
            )


def downgrade():
    op.drop_table('otx_state_log')
