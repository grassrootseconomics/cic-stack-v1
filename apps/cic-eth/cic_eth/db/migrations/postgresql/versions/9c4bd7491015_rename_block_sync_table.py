"""Rename block sync table

Revision ID: 9c4bd7491015
Revises: 9daa16518a91
Create Date: 2020-10-15 23:45:56.306898

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9c4bd7491015'
down_revision = '9daa16518a91'
branch_labels = None
depends_on = None


def upgrade():
    op.rename_table('block_sync', 'otx_sync')
    pass


def downgrade():
    op.rename_table('otx_sync', 'block_sync')
    pass
