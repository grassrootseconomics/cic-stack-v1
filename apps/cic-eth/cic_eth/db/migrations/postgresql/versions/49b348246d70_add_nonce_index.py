"""Add nonce index

Revision ID: 49b348246d70
Revises: 52c7c59cd0b1
Create Date: 2020-12-19 09:45:36.186446

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '49b348246d70'
down_revision = '52c7c59cd0b1'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'nonce',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('address_hex', sa.String(42), nullable=False, unique=True),
        sa.Column('nonce', sa.Integer, nullable=False),
        )


def downgrade():
    op.drop_table('nonce')
