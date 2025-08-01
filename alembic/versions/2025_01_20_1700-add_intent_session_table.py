"""add intent session table

Revision ID: 2b3f4a5e6c7d
Revises: 1a77684abf7d
Create Date: 2025-01-20 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2b3f4a5e6c7d'
down_revision = '1a77684abf7d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('intent_sessions',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('session_id', sa.String(), nullable=False),
    sa.Column('goal', sa.Text(), nullable=False),
    sa.Column('user_ip', sa.String(), nullable=True),
    sa.Column('user_country', sa.String(), nullable=True),
    sa.Column('generated_intents', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_intent_sessions_session_id'), 'intent_sessions', ['session_id'], unique=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_intent_sessions_session_id'), table_name='intent_sessions')
    op.drop_table('intent_sessions')
    # ### end Alembic commands ### 