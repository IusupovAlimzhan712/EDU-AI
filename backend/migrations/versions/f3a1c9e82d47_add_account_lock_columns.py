"""add account lock columns (UC-F1.2 E1)

Adds failedAttempts and lockedUntil to the student table to implement
brute-force protection: account is locked for 15 minutes after 5
consecutive failed login attempts.

Revision ID: f3a1c9e82d47
Revises: d81d90e2d651
Create Date: 2026-06-16 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f3a1c9e82d47'
down_revision = 'd81d90e2d651'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'student',
        sa.Column('failedAttempts', sa.Integer(), nullable=False, server_default='0'),
    )
    op.add_column(
        'student',
        sa.Column('lockedUntil', sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_column('student', 'lockedUntil')
    op.drop_column('student', 'failedAttempts')
