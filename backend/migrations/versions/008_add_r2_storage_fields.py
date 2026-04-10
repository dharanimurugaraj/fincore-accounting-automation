"""add r2 storage fields

Revision ID: 008
Revises: 007
Create Date: 2026-04-09 17:41:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade():
    # Adding orgFolder and runTimestamp to PipelineRun table
    op.add_column('PipelineRun', sa.Column('orgFolder', sa.String(), nullable=False, server_default=''))
    op.add_column('PipelineRun', sa.Column('runTimestamp', sa.String(length=15), nullable=False, server_default=''))


def downgrade():
    op.drop_column('PipelineRun', 'runTimestamp')
    op.drop_column('PipelineRun', 'orgFolder')
