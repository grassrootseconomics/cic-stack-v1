"""add tx sync state

Revision ID: 9daa16518a91
Revises: e3b5330ee71c
Create Date: 2020-10-10 14:43:18.699276

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9daa16518a91'
down_revision = 'e3b5330ee71c'
branch_labels = None
depends_on = None


def upgrade():
#    op.create_table(
#            'tx_sync',
#            sa.Column('tx', sa.String(66), nullable=False),
#            )
#    op.execute("INSERT INTO tx_sync VALUES('0x0000000000000000000000000000000000000000000000000000000000000000')")
    pass


def downgrade():
#    op.drop_table('tx_sync')
    pass
