"""add blocknumber pointer

Revision ID: 7cb65b893934
Revises: 8593fa1ca0f4
Create Date: 2020-09-24 19:29:13.543648

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7cb65b893934'
down_revision = '8593fa1ca0f4'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
            'watcher_state',
            sa.Column('block_number', sa.Integer)
            )
    conn = op.get_bind()
    conn.execute('INSERT INTO watcher_state (block_number) VALUES (0);')
    pass


def downgrade():
    op.drop_table('watcher_state')
    pass
