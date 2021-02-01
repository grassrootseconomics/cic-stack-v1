"""Add attempts and version log for otx

Revision ID: 71708e943dbd
Revises: 7e8d7626e38f
Create Date: 2020-09-26 14:41:19.298651

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '71708e943dbd'
down_revision = '7e8d7626e38f'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
            'otx_attempts',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('otx_id', sa.Integer, sa.ForeignKey('otx.id'), nullable=False),
            sa.Column('date', sa.DateTime, nullable=False),
            )
    pass


def downgrade():
    op.drop_table('otx_attempts')
    pass
