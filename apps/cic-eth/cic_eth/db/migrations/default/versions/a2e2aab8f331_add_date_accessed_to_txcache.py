"""Add date accessed to txcache

Revision ID: a2e2aab8f331
Revises: 49b348246d70
Create Date: 2020-12-24 18:58:06.137812

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a2e2aab8f331'
down_revision = '49b348246d70'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'tx_cache',
        sa.Column(
            'date_checked',
            sa.DateTime,
            nullable=False
        )
    )
    pass


def downgrade():
    # drop does not work withs qlite
    #op.drop_column('tx_cache', 'date_checked')
    pass
