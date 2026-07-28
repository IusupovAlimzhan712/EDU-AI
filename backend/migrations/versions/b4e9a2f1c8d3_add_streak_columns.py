"""add study streak columns to learning_progress

Adds currentStreak (consecutive study days) and lastStudyDate to
learning_progress so the dashboard can show a study streak counter.

Revision ID: b4e9a2f1c8d3
Revises: f3a1c9e82d47
Create Date: 2026-06-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'b4e9a2f1c8d3'
down_revision = 'f3a1c9e82d47'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'learning_progress',
        sa.Column('currentStreak', sa.Integer(), nullable=False, server_default='0'),
    )
    op.add_column(
        'learning_progress',
        sa.Column('lastStudyDate', sa.Date(), nullable=True),
    )


def downgrade():
    op.drop_column('learning_progress', 'lastStudyDate')
    op.drop_column('learning_progress', 'currentStreak')
