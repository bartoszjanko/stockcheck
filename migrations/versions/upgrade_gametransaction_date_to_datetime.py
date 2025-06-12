"""
Upgrade GameTransaction.date from Date to DateTime
"""

revision = '20250607_1'
down_revision = 'a0e75e4911b5'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

def upgrade():
    with op.batch_alter_table('game_transaction', schema=None) as batch_op:
        batch_op.alter_column('date',
            existing_type=sa.Date(),
            type_=sa.DateTime(),
            existing_nullable=True
        )

def downgrade():
    with op.batch_alter_table('game_transaction', schema=None) as batch_op:
        batch_op.alter_column('date',
            existing_type=sa.DateTime(),
            type_=sa.Date(),
            existing_nullable=True
        )
