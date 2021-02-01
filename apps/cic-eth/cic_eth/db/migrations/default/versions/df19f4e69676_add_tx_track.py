"""Add tx tracker record

Revision ID: df19f4e69676
Revises: 71708e943dbd
Create Date: 2020-10-09 23:31:44.563498

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'df19f4e69676'
down_revision = '71708e943dbd'
branch_labels = None
depends_on = None


def upgrade():
#    op.create_table(
#            'tx',
#            sa.Column('id', sa.Integer, primary_key=True),
#            sa.Column('date_added', sa.DateTime, nullable=False),
#            sa.Column('tx_hash', sa.String(66), nullable=False, unique=True),
#            sa.Column('success', sa.Boolean(), nullable=False),
#            )
    pass


def downgrade():
#    op.drop_table('tx')
    pass
