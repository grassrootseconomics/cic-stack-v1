"""Add block sync

Revision ID: 7e8d7626e38f
Revises: cd2052be6db2
Create Date: 2020-09-26 11:12:27.818524

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7e8d7626e38f'
down_revision = 'cd2052be6db2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
            'block_sync',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('blockchain', sa.String, nullable=False, unique=True),
            sa.Column('block_height_backlog', sa.Integer, nullable=False, default=0),
            sa.Column('tx_height_backlog', sa.Integer, nullable=False, default=0),
            sa.Column('block_height_session', sa.Integer, nullable=False, default=0),
            sa.Column('tx_height_session', sa.Integer, nullable=False, default=0),
            sa.Column('block_height_head', sa.Integer, nullable=False, default=0),
            sa.Column('tx_height_head', sa.Integer, nullable=False, default=0),
            sa.Column('date_created', sa.DateTime, nullable=False),
            sa.Column('date_updated', sa.DateTime),
            )
    op.drop_table('watcher_state')
    pass


def downgrade():
    op.drop_table('block_sync')
    op.create_table(
            'watcher_state',
            sa.Column('block_number', sa.Integer)
            )
    conn = op.get_bind()
    conn.execute('INSERT INTO watcher_state (block_number) VALUES (0);')
    pass
