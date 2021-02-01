"""convert tx index

Revision ID: cd2052be6db2
Revises: 7cb65b893934
Create Date: 2020-09-24 21:20:51.580500

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'cd2052be6db2'
down_revision = '7cb65b893934'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
            'tx_convert_transfer',
            sa.Column('id', sa.Integer, primary_key=True),
            #sa.Column('approve_tx_hash', sa.String(66), nullable=False, unique=True),
            sa.Column('convert_tx_hash', sa.String(66), nullable=False, unique=True),
            sa.Column('transfer_tx_hash', sa.String(66), unique=True),
#            sa.Column('holder_address', sa.String(42), nullable=False),
            sa.Column('recipient_address', sa.String(42), nullable=False),
            )
    op.create_index('idx_tx_convert_address', 'tx_convert_transfer', ['recipient_address'])


def downgrade():
    op.drop_index('idx_tx_convert_address')
    op.drop_table('tx_convert_transfer')
