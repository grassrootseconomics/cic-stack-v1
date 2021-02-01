"""Add account roles

Revision ID: 52c7c59cd0b1
Revises: 9c4bd7491015
Create Date: 2020-12-19 07:21:38.249237

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '52c7c59cd0b1'
down_revision = '9c4bd7491015'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
            'account_role',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('tag', sa.Text, nullable=False, unique=True),
            sa.Column('address_hex', sa.String(42), nullable=False),
            )
    pass


def downgrade():
    op.drop_table('account_role')
    pass
