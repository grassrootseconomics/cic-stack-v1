"""Notify sms log

Revision ID: b2aedf79b0b2
Revises: 
Create Date: 2020-10-11 15:59:02.765157

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2aedf79b0b2'
down_revision = None
branch_labels = None
depends_on = None

status_enum = sa.Enum(
    'UNKNOWN', # the state of the message is not known
    name='notification_status',
    )

transport_enum = sa.Enum(
    'SMS',
    name='notification_transport',
   )

def upgrade():
    op.create_table('notification',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('transport', transport_enum, nullable=False),
            sa.Column('status', status_enum, nullable=False),
            sa.Column('status_code', sa.String(), nullable=True),
            sa.Column('status_serial', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('recipient', sa.String(), nullable=False),
            sa.Column('created', sa.DateTime(), nullable=False),
            sa.Column('updated', sa.DateTime(), nullable=False),
            sa.Column('message', sa.String(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('notification_recipient_transport_idx', 'notification', ['transport', 'recipient'], schema=None, unique=False)


def downgrade():
    op.drop_index('notification_recipient_transport_idx')
    op.drop_table('notification')
    status_enum.drop(op.get_bind(), checkfirst=False)
    transport_enum.drop(op.get_bind(), checkfirst=False)
