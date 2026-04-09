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
    # Adding org_folder and run_timestamp to PipelineRun table
    op.add_column('PipelineRun', sa.Column('org_folder', sa.String(), nullable=False, server_default=''))
    op.add_column('PipelineRun', sa.Column('run_timestamp', sa.String(length=15), nullable=False, server_default=''))


def downgrade():
    op.drop_column('PipelineRun', 'run_timestamp')
    op.drop_column('PipelineRun', 'org_folder')
